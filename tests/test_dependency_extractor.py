"""Tests for src.crawler.dependency_extractor."""

from src.crawler.dependency_extractor import scan_project_di


def _by_method(regs):
    out = {}
    for r in regs:
        out.setdefault(r.method, []).append(r)
    return out


def test_extracts_lifetime_registrations(sample_solution):
    api_dir = sample_solution.parent / "Demo.Invoicing.Api"
    regs = scan_project_di(api_dir, project_name="Demo.Invoicing.Api")
    by = _by_method(regs)

    assert any(
        r.service_type == "IInvoiceRepository" and r.implementation == "InvoiceRepository"
        for r in by.get("AddSingleton", [])
    )
    assert any(
        r.service_type == "IClock" and r.implementation == "SystemClock"
        for r in by.get("AddScoped", [])
    )


def test_extracts_dbcontext(sample_solution):
    api_dir = sample_solution.parent / "Demo.Invoicing.Api"
    regs = scan_project_di(api_dir, project_name="Demo.Invoicing.Api")
    db = [r for r in regs if r.method == "AddDbContext"]
    assert any(r.service_type == "InvoiceDbContext" for r in db)


def test_extracts_named_http_clients(sample_solution):
    api_dir = sample_solution.parent / "Demo.Invoicing.Api"
    regs = scan_project_di(api_dir, project_name="Demo.Invoicing.Api")
    http = [r for r in regs if r.method == "AddHttpClient"]
    named = [r for r in http if r.named_client == "TaxpayerService"]
    # We expect both the bare AddHttpClient("TaxpayerService") and the
    # generic AddHttpClient<I, T>("TaxpayerService") to be captured.
    assert len(named) >= 1
    typed = [r for r in named if r.service_type == "ITaxpayerClient"]
    assert typed, "expected the generic+named overload to be captured"


def test_extracts_marker_calls(sample_solution):
    api_dir = sample_solution.parent / "Demo.Invoicing.Api"
    regs = scan_project_di(api_dir, project_name="Demo.Invoicing.Api")
    methods = {r.method for r in regs}
    assert "AddMediatR" in methods
    assert "AddMassTransit" in methods


def test_line_numbers_populated(sample_solution):
    api_dir = sample_solution.parent / "Demo.Invoicing.Api"
    regs = scan_project_di(api_dir, project_name="Demo.Invoicing.Api")
    assert all(r.line > 0 for r in regs)
