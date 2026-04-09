"""Tests for src.crawler.code_analyzer."""

from src.crawler.code_analyzer import scan_project_symbols


def _by_name(symbols):
    return {s.name: s for s in symbols}


def test_extracts_classes_records_and_namespace(sample_solution):
    dom_dir = sample_solution.parent / "Demo.Invoicing.Domain"
    syms = scan_project_symbols(dom_dir, project_name="Demo.Invoicing.Domain")
    by = _by_name(syms)

    assert "Invoice" in by
    assert by["Invoice"].kind == "class"
    assert by["Invoice"].namespace == "Demo.Invoicing.Domain"

    assert "InvoiceSubmittedEvent" in by
    assert by["InvoiceSubmittedEvent"].kind == "record"


def test_aggregate_root_flag(sample_solution):
    dom_dir = sample_solution.parent / "Demo.Invoicing.Domain"
    syms = scan_project_symbols(dom_dir)
    inv = next(s for s in syms if s.name == "Invoice")
    assert inv.is_aggregate_root is True


def test_domain_event_flag(sample_solution):
    dom_dir = sample_solution.parent / "Demo.Invoicing.Domain"
    syms = scan_project_symbols(dom_dir)
    evt = next(s for s in syms if s.name == "InvoiceSubmittedEvent")
    assert evt.is_domain_event is True


def test_controller_flag(sample_solution):
    api_dir = sample_solution.parent / "Demo.Invoicing.Api"
    syms = scan_project_symbols(api_dir)
    by = _by_name(syms)
    assert "InvoiceController" in by
    assert by["InvoiceController"].is_controller is True
    assert "ControllerBase" in by["InvoiceController"].base_types


def test_attributes_captured(sample_solution):
    api_dir = sample_solution.parent / "Demo.Invoicing.Api"
    syms = scan_project_symbols(api_dir)
    ctrl = next(s for s in syms if s.name == "InvoiceController")
    assert "Route" in ctrl.attributes
    assert "Authorize" in ctrl.attributes
