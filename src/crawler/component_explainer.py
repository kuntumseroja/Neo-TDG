"""Component and logic explainer using RAG + LLM."""

import re
import logging
from pathlib import Path
from typing import List, Optional

from src.models.flow import ComponentExplanation, ValidationRule
from src.models.crawler import UIComponent

logger = logging.getLogger(__name__)


class ComponentExplainer:
    """Explain classes, methods, and UI components using LLM and knowledge context."""

    def __init__(self, llm=None, vector_store=None):
        """
        Args:
            llm: BaseLLM instance for generating explanations
            vector_store: VectorKnowledgeStore for retrieving context
        """
        self.llm = llm
        self.store = vector_store

    def explain_class(self, file_path: str, class_name: str = "") -> ComponentExplanation:
        """Explain a C# class with its purpose, dependencies, and behavior."""
        content = self._read_file(file_path)
        if not content:
            return ComponentExplanation(
                name=class_name or Path(file_path).stem,
                file=file_path,
                explanation=f"Could not read file: {file_path}",
            )

        # Extract class info
        if not class_name:
            class_match = re.search(r"class\s+(\w+)", content)
            class_name = class_match.group(1) if class_match else Path(file_path).stem

        # Find class body
        class_body = self._extract_class_body(content, class_name)
        if not class_body:
            class_body = content

        # Extract dependencies (constructor injection)
        deps = self._extract_dependencies(class_body)

        # Extract domain events
        events = self._extract_domain_events(class_body)

        # Determine component type
        comp_type = self._classify_component(class_name, class_body)

        # Get RAG context if available
        rag_context = ""
        if self.store:
            chunks = self.store.query(f"What is {class_name}?", top_k=3)
            rag_context = "\n".join(c.content[:500] for c in chunks)

        # Generate explanation via LLM
        explanation = self._generate_explanation(class_name, class_body, comp_type, deps, rag_context)

        return ComponentExplanation(
            name=class_name,
            type=comp_type,
            file=file_path,
            explanation=explanation,
            business_rules=self._extract_business_rules(class_body),
            domain_events=events,
            dependencies=deps,
        )

    def explain_method(self, file_path: str, method_name: str) -> ComponentExplanation:
        """Explain a specific method within a file."""
        content = self._read_file(file_path)
        if not content:
            return ComponentExplanation(
                name=method_name, file=file_path,
                explanation=f"Could not read file: {file_path}",
            )

        method_body = self._extract_method_body(content, method_name)
        if not method_body:
            return ComponentExplanation(
                name=method_name, file=file_path,
                explanation=f"Method '{method_name}' not found in {file_path}",
            )

        explanation = ""
        if self.llm:
            prompt = (
                f"Explain this C# method in clear technical prose:\n\n"
                f"Method: {method_name}\n"
                f"```csharp\n{method_body[:2000]}\n```\n\n"
                f"Explain: purpose, inputs, outputs, business rules, and side effects."
            )
            try:
                explanation = self.llm.generate(prompt)
            except Exception as e:
                explanation = f"LLM explanation failed: {e}"

        return ComponentExplanation(
            name=method_name,
            type="method",
            file=file_path,
            explanation=explanation or f"Method: {method_name}",
            business_rules=self._extract_business_rules(method_body),
            domain_events=self._extract_domain_events(method_body),
        )

    def explain_ui_component(self, component: UIComponent) -> ComponentExplanation:
        """Explain an Angular UI component."""
        content = self._read_file(component.component_file)
        template_content = ""
        if component.template_file:
            template_path = str(
                Path(component.component_file).parent / component.template_file
            )
            template_content = self._read_file(template_path) or ""

        explanation = ""
        if self.llm:
            prompt = (
                f"Explain this Angular component:\n\n"
                f"Component: {component.name}\n"
                f"Selector: {component.selector}\n"
                f"API calls: {', '.join(component.api_calls) if component.api_calls else 'none'}\n\n"
                f"TypeScript:\n```typescript\n{(content or '')[:1500]}\n```\n\n"
                f"Template:\n```html\n{template_content[:1000]}\n```\n\n"
                f"Explain: purpose, user interactions, data flow, and API integrations."
            )
            try:
                explanation = self.llm.generate(prompt)
            except Exception as e:
                explanation = f"LLM explanation failed: {e}"

        return ComponentExplanation(
            name=component.name,
            type="ui_component",
            file=component.component_file,
            explanation=explanation or f"Angular component: {component.name}",
            dependencies=component.api_calls,
        )

    def explain_validation_rules(self, file_path: str) -> List[ValidationRule]:
        """Extract validation rules from a handler or validator class."""
        content = self._read_file(file_path)
        if not content:
            return []

        rules = []

        # FluentValidation rules
        for match in re.finditer(
            r"RuleFor\s*\(\s*\w+\s*=>\s*\w+\.(\w+)\)\s*\.([\w.()\"]+)",
            content, re.DOTALL,
        ):
            field = match.group(1)
            condition = match.group(2).strip()
            rules.append(ValidationRule(
                name=f"Validate {field}",
                field=field,
                condition=condition,
                file=file_path,
            ))

        # DataAnnotation attributes
        for match in re.finditer(
            r"\[(Required|MaxLength|MinLength|Range|RegularExpression|StringLength)"
            r"(?:\(([^)]*)\))?\]\s*\n\s*public\s+\w+\s+(\w+)",
            content,
        ):
            attr = match.group(1)
            params = match.group(2) or ""
            field = match.group(3)
            rules.append(ValidationRule(
                name=f"{attr} on {field}",
                field=field,
                condition=f"[{attr}({params})]" if params else f"[{attr}]",
                file=file_path,
            ))

        # If/throw patterns (manual validation)
        for match in re.finditer(
            r"if\s*\(([^)]+)\)\s*\n?\s*throw\s+new\s+(\w+)\s*\(\s*\"([^\"]+)\"",
            content,
        ):
            condition = match.group(1).strip()
            exception = match.group(2)
            message = match.group(3)
            rules.append(ValidationRule(
                name=message[:80],
                condition=condition,
                description=f"Throws {exception}: {message}",
                file=file_path,
            ))

        return rules

    def _generate_explanation(
        self, class_name: str, class_body: str, comp_type: str,
        deps: List[str], rag_context: str,
    ) -> str:
        """Generate explanation via LLM."""
        if not self.llm:
            return f"{comp_type}: {class_name} with dependencies: {', '.join(deps)}"

        prompt = (
            f"Explain this C# {comp_type} in clear technical prose:\n\n"
            f"Class: {class_name}\n"
            f"Type: {comp_type}\n"
            f"Dependencies: {', '.join(deps) if deps else 'none'}\n\n"
            f"```csharp\n{class_body[:2000]}\n```\n\n"
        )
        if rag_context:
            prompt += f"Additional context from knowledge base:\n{rag_context[:1000]}\n\n"
        prompt += "Explain: purpose, architecture role, key behaviors, and domain significance."

        try:
            return self.llm.generate(prompt)
        except Exception as e:
            return f"LLM explanation failed: {e}"

    @staticmethod
    def _read_file(file_path: str) -> Optional[str]:
        """Read file content."""
        try:
            return Path(file_path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None

    @staticmethod
    def _extract_class_body(content: str, class_name: str) -> Optional[str]:
        """Extract the body of a named class."""
        pattern = re.compile(rf"class\s+{re.escape(class_name)}\b[^{{]*\{{", re.DOTALL)
        match = pattern.search(content)
        if not match:
            return None
        start = match.start()
        brace_count = 0
        for i, ch in enumerate(content[start:], start):
            if ch == "{":
                brace_count += 1
            elif ch == "}":
                brace_count -= 1
                if brace_count == 0:
                    return content[start:i + 1]
        return content[start:]

    @staticmethod
    def _extract_method_body(content: str, method_name: str) -> Optional[str]:
        """Extract a method body by name."""
        pattern = re.compile(
            rf"(?:public|private|protected|internal)\s+\w+\s+{re.escape(method_name)}\s*\([^)]*\)\s*\{{",
            re.DOTALL,
        )
        match = pattern.search(content)
        if not match:
            return None
        start = match.start()
        brace_count = 0
        for i, ch in enumerate(content[start:], start):
            if ch == "{":
                brace_count += 1
            elif ch == "}":
                brace_count -= 1
                if brace_count == 0:
                    return content[start:i + 1]
        return content[start:]

    @staticmethod
    def _extract_dependencies(class_body: str) -> List[str]:
        """Extract constructor-injected dependencies."""
        # Match constructor parameters
        ctor_match = re.search(
            r"(?:public|internal)\s+\w+\s*\(([^)]+)\)", class_body
        )
        if not ctor_match:
            return []
        params = ctor_match.group(1)
        return re.findall(r"(\w+(?:<\w+>)?)\s+\w+", params)

    @staticmethod
    def _extract_domain_events(code: str) -> List[str]:
        """Extract domain events published or consumed."""
        events = set()
        for match in re.finditer(r"Publish<(\w+)>|new\s+(\w+Event)\s*\(", code):
            event = match.group(1) or match.group(2)
            if event:
                events.add(event)
        return sorted(events)

    @staticmethod
    def _extract_business_rules(code: str) -> List[str]:
        """Extract business rules from validation logic."""
        rules = []
        for match in re.finditer(r'throw\s+new\s+\w+\(\s*"([^"]+)"', code):
            rules.append(match.group(1))
        return rules[:10]

    @staticmethod
    def _classify_component(name: str, body: str) -> str:
        """Classify a component by its name and content."""
        name_lower = name.lower()
        if "controller" in name_lower:
            return "controller"
        if "handler" in name_lower:
            return "handler"
        if "consumer" in name_lower:
            return "consumer"
        if "validator" in name_lower:
            return "validator"
        if "repository" in name_lower:
            return "repository"
        if "service" in name_lower:
            return "service"
        if "saga" in name_lower:
            return "saga"
        if re.search(r":\s*.*?DbContext", body):
            return "db_context"
        if re.search(r":\s*.*?AggregateRoot|IAggregateRoot", body):
            return "aggregate"
        return "class"
