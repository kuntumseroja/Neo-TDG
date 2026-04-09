"""Tests for src.crawler.domain_mapper and the end-to-end SolutionCrawler
deep-analysis wiring."""

from src.crawler.solution_crawler import SolutionCrawler


def test_crawler_with_deep_analysis_populates_domains(sample_solution):
    crawler = SolutionCrawler({"deep_analysis": {"enabled": True}})
    report = crawler.crawl(str(sample_solution))

    assert len(report.projects) == 3

    # Per-project deep fields populated
    api = next(p for p in report.projects if p.name == "Demo.Invoicing.Api")
    assert api.configurations, "expected appsettings nodes on the API project"
    assert api.di_registrations, "expected DI registrations from Program.cs"
    assert api.code_symbols, "expected code symbols on the API project"

    # Business domains: project clustering should produce at least Invoicing + Taxpayer
    domain_names = {d.name for d in report.business_domains}
    assert "Invoicing" in domain_names
    assert "Taxpayer" in domain_names

    invoicing = next(d for d in report.business_domains if d.name == "Invoicing")
    assert "Demo.Invoicing.Api" in invoicing.projects
    assert "Demo.Invoicing.Domain" in invoicing.projects
    assert "InvoiceSubmittedEvent" in invoicing.domain_events
    assert "Invoice" in invoicing.aggregates


def test_contracts_link_invoicing_to_taxpayer(sample_solution):
    crawler = SolutionCrawler({"deep_analysis": {"enabled": True}})
    report = crawler.crawl(str(sample_solution))

    contracts = report.domain_contracts
    assert contracts, "expected at least one domain contract"

    # The named HttpClient "TaxpayerService" should resolve to the Taxpayer domain
    taxpayer_contracts = [
        c for c in contracts
        if c.transport == "http" and c.target_service == "TaxpayerService"
    ]
    assert taxpayer_contracts, "expected an HTTP contract pointing at TaxpayerService"

    invoicing = next(d for d in report.business_domains if d.name == "Invoicing")
    taxpayer = next(d for d in report.business_domains if d.name == "Taxpayer")
    assert "Taxpayer" in invoicing.outbound_contracts
    assert "Invoicing" in taxpayer.inbound_contracts


def test_disabled_deep_analysis_is_noop(sample_solution):
    """When deep_analysis is off, the new fields stay empty and the
    legacy crawl output is unchanged."""
    crawler = SolutionCrawler({})  # default: disabled
    report = crawler.crawl(str(sample_solution))

    assert report.business_domains == []
    assert report.domain_contracts == []
    for project in report.projects:
        assert project.configurations == []
        assert project.di_registrations == []
        assert project.code_symbols == []

    # Legacy fields still work
    assert any(ep.controller == "InvoiceController" for ep in report.endpoints)
