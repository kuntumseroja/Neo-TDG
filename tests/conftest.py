"""Shared pytest fixtures for the deep-code-analysis test suite.

Builds an in-memory synthetic .NET-style project tree on disk so the
analyzers can be exercised end-to-end without depending on the
``examples/CoreTaxSample`` (which is heavyweight) or any external code.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

# Make `src.*` importable when running pytest from the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@pytest.fixture
def sample_solution(tmp_path: Path) -> Path:
    """Create a tiny synthetic .NET solution and return the .sln path.

    Layout:
        Demo.sln
        Demo.Invoicing.Domain/
            Demo.Invoicing.Domain.csproj
            Invoice.cs                  (aggregate root)
            InvoiceSubmittedEvent.cs    (domain event)
        Demo.Invoicing.Api/
            Demo.Invoicing.Api.csproj
            Program.cs                  (DI registrations)
            InvoiceController.cs        (HTTP endpoint)
            appsettings.json
            appsettings.Development.json
            launchSettings.json
        Demo.Taxpayer.Api/
            Demo.Taxpayer.Api.csproj
            TaxpayerController.cs
            appsettings.json
    """
    sln = tmp_path / "Demo.sln"
    sln.write_text(textwrap.dedent("""\
        Microsoft Visual Studio Solution File, Format Version 12.00
        Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "Demo.Invoicing.Domain", "Demo.Invoicing.Domain/Demo.Invoicing.Domain.csproj", "{11111111-1111-1111-1111-111111111111}"
        EndProject
        Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "Demo.Invoicing.Api", "Demo.Invoicing.Api/Demo.Invoicing.Api.csproj", "{22222222-2222-2222-2222-222222222222}"
        EndProject
        Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "Demo.Taxpayer.Api", "Demo.Taxpayer.Api/Demo.Taxpayer.Api.csproj", "{33333333-3333-3333-3333-333333333333}"
        EndProject
    """))

    # ── Demo.Invoicing.Domain ──────────────────────────────────────────
    dom = tmp_path / "Demo.Invoicing.Domain"
    dom.mkdir()
    (dom / "Demo.Invoicing.Domain.csproj").write_text(textwrap.dedent("""\
        <Project Sdk="Microsoft.NET.Sdk">
          <PropertyGroup>
            <TargetFramework>net8.0</TargetFramework>
          </PropertyGroup>
        </Project>
    """))
    (dom / "Invoice.cs").write_text(textwrap.dedent("""\
        namespace Demo.Invoicing.Domain;

        public class Invoice : AggregateRoot
        {
            public Guid Id { get; set; }
        }
    """))
    (dom / "InvoiceSubmittedEvent.cs").write_text(textwrap.dedent("""\
        namespace Demo.Invoicing.Domain;

        public record InvoiceSubmittedEvent(Guid InvoiceId) : INotification;
    """))

    # ── Demo.Invoicing.Api ─────────────────────────────────────────────
    api = tmp_path / "Demo.Invoicing.Api"
    api.mkdir()
    (api / "Demo.Invoicing.Api.csproj").write_text(textwrap.dedent("""\
        <Project Sdk="Microsoft.NET.Sdk.Web">
          <PropertyGroup>
            <TargetFramework>net8.0</TargetFramework>
          </PropertyGroup>
          <ItemGroup>
            <ProjectReference Include="..\\Demo.Invoicing.Domain\\Demo.Invoicing.Domain.csproj" />
            <PackageReference Include="MediatR" Version="12.0.0" />
          </ItemGroup>
        </Project>
    """))
    (api / "Program.cs").write_text(textwrap.dedent("""\
        var builder = WebApplication.CreateBuilder(args);
        IServiceCollection services = builder.Services;

        services.AddSingleton<IInvoiceRepository, InvoiceRepository>();
        services.AddScoped<IClock, SystemClock>();
        services.AddDbContext<InvoiceDbContext>(opt => opt.UseSqlServer("..."));
        services.AddHttpClient("TaxpayerService");
        services.AddHttpClient<ITaxpayerClient, TaxpayerClient>("TaxpayerService");
        services.AddMediatR(typeof(Program));
        services.AddMassTransit(x => { });
    """))
    (api / "InvoiceController.cs").write_text(textwrap.dedent("""\
        namespace Demo.Invoicing.Api.Controllers;

        [Route("api/invoices")]
        [Authorize]
        public class InvoiceController : ControllerBase
        {
            [HttpPost("submit")]
            public async Task<IActionResult> Submit() { return Ok(); }

            [HttpGet("{id}")]
            public async Task<IActionResult> Get(Guid id) { return Ok(); }
        }
    """))
    (api / "appsettings.json").write_text(textwrap.dedent("""\
        {
          "ConnectionStrings": {
            "Default": "Server=localhost;Database=Invoicing;"
          },
          "TaxpayerService": {
            "BaseUrl": "https://taxpayer.example.com",
            "TimeoutSeconds": 30
          },
          "FeatureManagement": {
            "NewInvoiceFlow": true
          }
        }
    """))
    (api / "appsettings.Development.json").write_text(textwrap.dedent("""\
        {
          "TaxpayerService": {
            "BaseUrl": "${TAXPAYER_URL}"
          }
        }
    """))
    (api / "launchSettings.json").write_text(textwrap.dedent("""\
        {
          "profiles": {
            "Demo.Invoicing.Api": {
              "applicationUrl": "https://localhost:5001;http://localhost:5000",
              "environmentVariables": {
                "ASPNETCORE_ENVIRONMENT": "Development"
              }
            }
          }
        }
    """))

    # ── Demo.Taxpayer.Api ──────────────────────────────────────────────
    tp = tmp_path / "Demo.Taxpayer.Api"
    tp.mkdir()
    (tp / "Demo.Taxpayer.Api.csproj").write_text(textwrap.dedent("""\
        <Project Sdk="Microsoft.NET.Sdk.Web">
          <PropertyGroup>
            <TargetFramework>net8.0</TargetFramework>
          </PropertyGroup>
        </Project>
    """))
    (tp / "TaxpayerController.cs").write_text(textwrap.dedent("""\
        namespace Demo.Taxpayer.Api.Controllers;

        [Route("api/taxpayers")]
        public class TaxpayerController : ControllerBase
        {
            [HttpGet]
            public async Task<IActionResult> List() { return Ok(); }
        }
    """))
    (tp / "appsettings.json").write_text(textwrap.dedent("""\
        {
          "Service": { "Name": "Taxpayer" }
        }
    """))

    return sln
