"""End-to-end flow tracing and explanation."""

import re
import logging
from typing import Optional, List

from src.models.crawler import CrawlReport, EndpointInfo, ConsumerInfo
from src.models.flow import FlowExplanation, FlowStep

logger = logging.getLogger(__name__)


class FlowExplainer:
    """Trace and explain business flows end-to-end with natural language."""

    def __init__(self, crawl_report: CrawlReport = None, llm=None):
        """
        Args:
            crawl_report: Pre-crawled solution report
            llm: BaseLLM instance for NL explanation generation
        """
        self.report = crawl_report
        self.llm = llm

    def explain_flow(self, entry_point: str) -> FlowExplanation:
        """
        Given an entry point (e.g., "POST /api/invoice/submit" or "InvoiceController.Submit"),
        trace the full flow through the system.
        """
        # Identify the starting endpoint or component
        endpoint = self._find_endpoint(entry_point)
        steps = []
        order = 1

        if endpoint:
            # Step 1: HTTP entry
            steps.append(FlowStep(
                order=order,
                component=f"{endpoint.controller}.{entry_point.split('.')[-1] if '.' in entry_point else 'Handle'}()",
                file=endpoint.file,
                line=endpoint.line,
                action=f"Receives HTTP {endpoint.method} at {endpoint.route}",
                type="http_entry",
            ))
            order += 1

            # Step 2: Look for command/query dispatch in controller code
            controller_code = self._read_file(endpoint.file)
            if controller_code:
                commands = re.findall(r"Send<(\w+)>|Publish<(\w+)>|new\s+(\w+(?:Command|Query))", controller_code)
                for match in commands:
                    cmd_name = match[0] or match[1] or match[2]
                    if cmd_name:
                        msg_type = "command" if "Command" in cmd_name or match[0] else "event"
                        steps.append(FlowStep(
                            order=order,
                            component=cmd_name,
                            file=endpoint.file,
                            action=f"Creates and dispatches {cmd_name} via MediatR/MassTransit",
                            type=msg_type,
                        ))
                        order += 1

                        # Step 3: Find handler
                        handler = self._find_handler(cmd_name)
                        if handler:
                            steps.append(FlowStep(
                                order=order,
                                component=handler,
                                file="",
                                action=f"Handles {cmd_name} — executes business logic",
                                type="handler",
                            ))
                            order += 1

                # Look for published events/messages
                publishes = re.findall(r"\.Publish<(\w+)>", controller_code)
                sends = re.findall(r"\.Send<(\w+)>", controller_code)

                for msg in publishes + sends:
                    steps.append(FlowStep(
                        order=order,
                        component=f"Publish {msg}",
                        file=endpoint.file,
                        action=f"Publishes {msg} to message bus",
                        type="event",
                    ))
                    order += 1

                    # Find consumers
                    consumers = self._find_consumers(msg)
                    for consumer in consumers:
                        steps.append(FlowStep(
                            order=order,
                            component=consumer.consumer_class,
                            file=consumer.file,
                            action=f"Consumes {msg} — processes downstream logic",
                            type="consumer",
                        ))
                        order += 1

                # Look for repository/database operations
                if re.search(r"SaveChanges|Repository|\.Add\(|\.Update\(|\.Remove\(", controller_code):
                    steps.append(FlowStep(
                        order=order,
                        component="Repository/DbContext",
                        file=endpoint.file,
                        action="Persists changes to database",
                        type="repository",
                    ))
                    order += 1
        else:
            # Try to find as a consumer or handler
            consumers = self._find_consumers(entry_point)
            if consumers:
                for consumer in consumers:
                    steps.append(FlowStep(
                        order=order,
                        component=consumer.consumer_class,
                        file=consumer.file,
                        action=f"Consumes message {consumer.message_type}",
                        type="consumer",
                    ))
                    order += 1

        # Generate diagram
        diagram = self._generate_sequence_diagram(steps)

        # Generate NL explanation
        explanation = self._generate_explanation(entry_point, steps)

        return FlowExplanation(
            title=f"Flow: {entry_point}",
            steps=steps,
            diagram=diagram,
            explanation=explanation,
            entry_point=entry_point,
        )

    def generate_sequence_diagram(self, flow: FlowExplanation) -> str:
        """Generate a Mermaid sequence diagram from a flow explanation."""
        return self._generate_sequence_diagram(flow.steps)

    def _find_endpoint(self, entry_point: str) -> Optional[EndpointInfo]:
        """Find an endpoint matching the entry point description."""
        if not self.report:
            return None

        entry_lower = entry_point.lower()
        for ep in self.report.endpoints:
            # Match by route
            if ep.route.lower() in entry_lower or entry_lower in ep.route.lower():
                return ep
            # Match by controller.method
            if ep.controller.lower() in entry_lower:
                return ep
        return None

    def _find_handler(self, command_name: str) -> Optional[str]:
        """Find a handler class for a given command/query name."""
        handler_name = f"{command_name}Handler"
        # Search in crawl report data models and consumers
        if self.report:
            for project in self.report.projects:
                if handler_name.lower() in project.name.lower():
                    return handler_name
        return handler_name  # Return expected name even if not found

    def _find_consumers(self, message_type: str) -> List[ConsumerInfo]:
        """Find consumers for a given message type."""
        if not self.report:
            return []
        return [
            c for c in self.report.consumers
            if c.message_type.lower() == message_type.lower()
            or message_type.lower() in c.message_type.lower()
        ]

    def _read_file(self, file_path: str) -> Optional[str]:
        """Read a source file's content."""
        try:
            from pathlib import Path
            p = Path(file_path)
            if p.exists():
                return p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass
        return None

    def _generate_sequence_diagram(self, steps: List[FlowStep]) -> str:
        """Generate Mermaid sequence diagram from flow steps."""
        if not steps:
            return ""

        lines = ["sequenceDiagram"]
        participants = []

        # Collect unique participants
        for step in steps:
            name = self._sanitize_participant(step.component)
            if name and name not in participants:
                participants.append(name)
                lines.append(f"    participant {name}")

        prev = None
        for step in steps:
            current = self._sanitize_participant(step.component)
            if not current:
                continue

            if prev and prev != current:
                arrow = "->>" if step.type in ("event", "consumer") else "->>"
                label = step.action[:60] if step.action else step.type
                lines.append(f"    {prev}{arrow}{current}: {label}")

            prev = current

        return "\n".join(lines)

    def _generate_explanation(self, entry_point: str, steps: List[FlowStep]) -> str:
        """Generate natural language explanation using LLM or fallback."""
        if self.llm and steps:
            step_text = "\n".join(
                f"{s.order}. [{s.type}] {s.component}: {s.action}" for s in steps
            )
            prompt = (
                f"Explain the following technical flow in clear, concise prose. "
                f"Entry point: {entry_point}\n\nSteps:\n{step_text}\n\n"
                f"Write a 2-3 paragraph explanation of this flow."
            )
            try:
                return self.llm.generate(prompt)
            except Exception as e:
                logger.warning(f"LLM explanation failed: {e}")

        # Fallback: simple text explanation
        if not steps:
            return f"No flow steps found for entry point: {entry_point}"

        lines = [f"The flow begins at **{entry_point}**.\n"]
        for step in steps:
            lines.append(f"{step.order}. **{step.component}** ({step.type}): {step.action}")
        return "\n".join(lines)

    @staticmethod
    def _sanitize_participant(name: str) -> str:
        """Sanitize a participant name for Mermaid."""
        name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        return name[:30] if name else ""
