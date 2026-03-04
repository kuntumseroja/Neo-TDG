"""AI-powered test case generator using RAG context."""

import logging
from pathlib import Path
from typing import List

from src.models.sdlc import TestCase, EdgeCase

logger = logging.getLogger(__name__)


class TestCaseGenerator:
    """Generate test cases for components using RAG context and LLM."""

    def __init__(self, rag_engine=None, llm=None):
        self.rag = rag_engine
        self.llm = llm

    def generate_unit_tests(self, component_path: str) -> str:
        """Generate xUnit C# unit test code for a component."""
        content = self._read_file(component_path)
        if not content:
            return f"// Could not read file: {component_path}"

        # Get RAG context about the component
        rag_context = ""
        if self.rag:
            try:
                result = self.rag.query(
                    question=f"What does the component in {Path(component_path).name} do? What are its dependencies and business rules?",
                    mode="explain",
                )
                rag_context = result.answer[:1500]
            except Exception:
                pass

        if not self.llm:
            return self._fallback_unit_tests(content, component_path)

        prompt = (
            f"Generate comprehensive xUnit C# unit tests for this component.\n\n"
            f"File: {Path(component_path).name}\n\n"
            f"```csharp\n{content[:3000]}\n```\n\n"
        )
        if rag_context:
            prompt += f"Context about this component:\n{rag_context}\n\n"
        prompt += (
            "Requirements:\n"
            "1. Use xUnit with [Fact] and [Theory] attributes\n"
            "2. Use Moq for mocking dependencies\n"
            "3. Follow Arrange-Act-Assert pattern\n"
            "4. Test happy paths, error cases, and edge cases\n"
            "5. Use meaningful test names following Should_ExpectedBehavior_When_Condition pattern\n"
            "6. Output only the C# test file code\n"
        )

        try:
            return self.llm.generate(prompt)
        except Exception as e:
            return f"// LLM generation failed: {e}\n\n{self._fallback_unit_tests(content, component_path)}"

    def generate_integration_tests(self, component_path: str) -> str:
        """Generate integration test code for cross-service flows."""
        content = self._read_file(component_path)
        if not content:
            return f"// Could not read file: {component_path}"

        rag_context = ""
        if self.rag:
            try:
                result = self.rag.query(
                    question=f"What services and message flows does {Path(component_path).name} interact with?",
                    mode="trace",
                )
                rag_context = result.answer[:1500]
            except Exception:
                pass

        if not self.llm:
            return f"// Integration test generation requires LLM. File: {component_path}"

        prompt = (
            f"Generate xUnit C# integration tests for this component and its cross-service interactions.\n\n"
            f"File: {Path(component_path).name}\n\n"
            f"```csharp\n{content[:2000]}\n```\n\n"
        )
        if rag_context:
            prompt += f"Service interaction context:\n{rag_context}\n\n"
        prompt += (
            "Requirements:\n"
            "1. Use WebApplicationFactory for API integration tests\n"
            "2. Test full request-response cycles\n"
            "3. Test message publishing and consumption\n"
            "4. Use TestContainers or in-memory alternatives for dependencies\n"
            "5. Output only the C# test file code\n"
        )

        try:
            return self.llm.generate(prompt)
        except Exception as e:
            return f"// LLM generation failed: {e}"

    def suggest_edge_cases(self, component_path: str) -> List[EdgeCase]:
        """Identify edge cases for a component based on its logic."""
        content = self._read_file(component_path)
        if not content:
            return []

        rag_context = ""
        if self.rag:
            try:
                result = self.rag.query(
                    question=f"What validation rules and edge cases exist in {Path(component_path).name}?",
                    mode="test",
                )
                rag_context = result.answer[:1500]
            except Exception:
                pass

        if not self.llm:
            return self._fallback_edge_cases(content, component_path)

        prompt = (
            f"Identify edge cases for testing this component.\n\n"
            f"File: {Path(component_path).name}\n\n"
            f"```csharp\n{content[:2500]}\n```\n\n"
        )
        if rag_context:
            prompt += f"Context:\n{rag_context}\n\n"
        prompt += (
            "For each edge case, provide:\n"
            "1. Name (short descriptive name)\n"
            "2. Description (what makes this an edge case)\n"
            "3. Input scenario (what input triggers it)\n"
            "4. Expected behavior (what should happen)\n\n"
            "List 5-10 edge cases, one per line in format: NAME | DESCRIPTION | INPUT | EXPECTED"
        )

        try:
            response = self.llm.generate(prompt)
            return self._parse_edge_cases(response, component_path)
        except Exception as e:
            logger.error(f"Edge case generation failed: {e}")
            return self._fallback_edge_cases(content, component_path)

    def _parse_edge_cases(self, response: str, component_path: str) -> List[EdgeCase]:
        """Parse LLM response into EdgeCase objects."""
        cases = []
        for line in response.split("\n"):
            line = line.strip().strip("*- ")
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 4:
                    cases.append(EdgeCase(
                        name=parts[0][:80],
                        description=parts[1][:200],
                        input_scenario=parts[2][:200],
                        expected_behavior=parts[3][:200],
                        component=Path(component_path).stem,
                    ))
            elif line and len(line) > 10:
                cases.append(EdgeCase(
                    name=line[:80],
                    description=line[:200],
                    component=Path(component_path).stem,
                ))
            if len(cases) >= 10:
                break
        return cases

    def _fallback_unit_tests(self, content: str, component_path: str) -> str:
        """Generate basic test skeleton without LLM."""
        import re
        class_match = re.search(r"class\s+(\w+)", content)
        class_name = class_match.group(1) if class_match else "Component"
        methods = re.findall(r"public\s+\w+\s+(\w+)\s*\(", content)

        lines = [
            "using Xunit;",
            "using Moq;",
            "",
            f"public class {class_name}Tests",
            "{",
        ]
        for method in methods[:10]:
            lines.extend([
                f"    [Fact]",
                f"    public void Should_Succeed_When_{method}_CalledWithValidInput()",
                f"    {{",
                f"        // Arrange",
                f"        // TODO: Setup mocks and test data",
                f"",
                f"        // Act",
                f"        // TODO: Call {method}",
                f"",
                f"        // Assert",
                f"        // TODO: Verify expected behavior",
                f"    }}",
                f"",
            ])
        lines.append("}")
        return "\n".join(lines)

    def _fallback_edge_cases(self, content: str, component_path: str) -> List[EdgeCase]:
        """Generate basic edge cases without LLM."""
        import re
        cases = []

        # Null/empty inputs
        params = re.findall(r"(\w+)\s+(\w+)[,)]", content)
        for param_type, param_name in params[:5]:
            if param_type in ["string", "String"]:
                cases.append(EdgeCase(
                    name=f"Null {param_name}",
                    description=f"Pass null for {param_name} parameter",
                    input_scenario=f"{param_name} = null",
                    expected_behavior="Should throw ArgumentNullException",
                    component=Path(component_path).stem,
                ))

        # Boundary conditions
        if "int" in content or "decimal" in content:
            cases.append(EdgeCase(
                name="Boundary values",
                description="Test with min/max numeric values",
                input_scenario="int.MaxValue, int.MinValue, 0",
                expected_behavior="Should handle gracefully",
                component=Path(component_path).stem,
            ))

        return cases

    @staticmethod
    def _read_file(file_path: str) -> str:
        """Read file content."""
        try:
            return Path(file_path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""
