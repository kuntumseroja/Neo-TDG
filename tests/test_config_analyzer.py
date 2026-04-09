"""Tests for src.crawler.config_analyzer."""

from src.crawler.config_analyzer import scan_project_configs


def test_scans_appsettings_and_launch(sample_solution):
    api_dir = sample_solution.parent / "Demo.Invoicing.Api"
    nodes = scan_project_configs(api_dir, project_name="Demo.Invoicing.Api")

    keys = {n.key for n in nodes}
    # Plain settings
    assert "ConnectionStrings.Default" in keys
    assert "TaxpayerService.BaseUrl" in keys
    assert "TaxpayerService.TimeoutSeconds" in keys
    # Launch profile
    assert any(k.startswith("profiles.Demo.Invoicing.Api.applicationUrl") for k in keys)
    # Feature management
    assert "FeatureManagement.NewInvoiceFlow" in keys


def test_classifies_kinds(sample_solution):
    api_dir = sample_solution.parent / "Demo.Invoicing.Api"
    nodes = scan_project_configs(api_dir, project_name="Demo.Invoicing.Api")
    by_key = {n.key: n for n in nodes}

    assert by_key["ConnectionStrings.Default"].kind == "connection_string"
    assert by_key["TaxpayerService.BaseUrl"].kind == "url"
    assert by_key["FeatureManagement.NewInvoiceFlow"].kind == "feature_flag"


def test_environment_label_set(sample_solution):
    api_dir = sample_solution.parent / "Demo.Invoicing.Api"
    nodes = scan_project_configs(api_dir, project_name="Demo.Invoicing.Api")
    dev_nodes = [n for n in nodes if n.environment == "Development"]
    assert dev_nodes, "expected at least one node from appsettings.Development.json"


def test_env_var_reference_extracted(sample_solution):
    api_dir = sample_solution.parent / "Demo.Invoicing.Api"
    nodes = scan_project_configs(api_dir, project_name="Demo.Invoicing.Api")
    dev_url = next(
        n for n in nodes
        if n.environment == "Development" and n.key == "TaxpayerService.BaseUrl"
    )
    assert dev_url.references_env_var == "TAXPAYER_URL"


def test_missing_dir_returns_empty(tmp_path):
    assert scan_project_configs(tmp_path / "does-not-exist") == []
