"""Angular UI component discovery."""

import re
from pathlib import Path
from typing import List
import logging

from src.models.crawler import UIComponent

logger = logging.getLogger(__name__)

# Angular patterns
_MODULE_ROUTES = re.compile(
    r"(?:path|loadChildren)\s*:\s*['\"]([^'\"]+)['\"]",
)
_COMPONENT_DECORATOR = re.compile(
    r"@Component\s*\(\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)?\}",
    re.DOTALL,
)
_SELECTOR_PATTERN = re.compile(r"selector\s*:\s*['\"]([^'\"]+)['\"]")
_TEMPLATE_URL_PATTERN = re.compile(r"templateUrl\s*:\s*['\"]([^'\"]+)['\"]")
_SERVICE_INJECT = re.compile(
    r"(?:private|public|protected)\s+(?:readonly\s+)?(\w+Service)\s*:",
)
_HTTP_CALL = re.compile(
    r"this\.http\.(?:get|post|put|delete|patch)\s*[<(]\s*['\"]?([^'\")\s,]+)",
)
_NGRX_STORE = re.compile(r"Store<(\w+)>")
_NGRX_EFFECT = re.compile(r"createEffect\s*\(")
_NGRX_ACTION = re.compile(r"createAction\s*\(\s*['\"]([^'\"]+)['\"]")


def discover_ui_components(angular_path: str) -> List[UIComponent]:
    """Discover Angular components, modules, and their relationships."""
    root = Path(angular_path)
    if not root.exists():
        logger.warning(f"Angular path not found: {angular_path}")
        return []

    components = []

    # Find all .component.ts files
    for comp_file in root.rglob("*.component.ts"):
        try:
            content = comp_file.read_text(encoding="utf-8", errors="ignore")
            component = _parse_component(content, comp_file)
            if component:
                components.append(component)
        except Exception as e:
            logger.warning(f"Error parsing {comp_file}: {e}")

    # Find modules and their routes
    for mod_file in root.rglob("*.module.ts"):
        try:
            content = mod_file.read_text(encoding="utf-8", errors="ignore")
            routes = _MODULE_ROUTES.findall(content)
            module_name = mod_file.stem.replace(".module", "")

            # Associate routes with components in this module
            for comp in components:
                if comp.module == "" and str(mod_file.parent) in comp.component_file:
                    comp.module = module_name
                    comp.routes = routes
        except Exception as e:
            logger.warning(f"Error parsing module {mod_file}: {e}")

    # Find service API calls
    for svc_file in root.rglob("*.service.ts"):
        try:
            content = svc_file.read_text(encoding="utf-8", errors="ignore")
            api_calls = _HTTP_CALL.findall(content)
            service_name = svc_file.stem.replace(".service", "")

            # Associate with components that inject this service
            for comp in components:
                if service_name in str(comp.component_file) or any(
                    service_name.lower() in s.lower()
                    for s in _get_injected_services(comp.component_file)
                ):
                    comp.api_calls.extend(api_calls)
        except Exception as e:
            logger.warning(f"Error parsing service {svc_file}: {e}")

    logger.info(f"Discovered {len(components)} Angular components in {angular_path}")
    return components


def _parse_component(content: str, file_path: Path) -> UIComponent | None:
    """Parse a .component.ts file for component metadata."""
    decorator = _COMPONENT_DECORATOR.search(content)
    if not decorator:
        return None

    decorator_body = decorator.group(1) or ""

    selector_match = _SELECTOR_PATTERN.search(decorator_body)
    template_match = _TEMPLATE_URL_PATTERN.search(decorator_body)

    selector = selector_match.group(1) if selector_match else ""
    template_url = template_match.group(1) if template_match else ""

    # Extract component name from class definition
    class_match = re.search(r"export\s+class\s+(\w+)", content)
    name = class_match.group(1) if class_match else file_path.stem

    # Find injected services
    services = _SERVICE_INJECT.findall(content)

    # Find HTTP calls within the component
    api_calls = _HTTP_CALL.findall(content)

    return UIComponent(
        name=name,
        selector=selector,
        template_file=template_url,
        component_file=str(file_path),
        api_calls=api_calls,
    )


def _get_injected_services(component_file: str) -> List[str]:
    """Get list of services injected into a component."""
    try:
        content = Path(component_file).read_text(encoding="utf-8", errors="ignore")
        return _SERVICE_INJECT.findall(content)
    except Exception:
        return []
