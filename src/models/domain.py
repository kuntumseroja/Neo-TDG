"""Deep code analysis domain models.

Pydantic models for the deep code/config/dependency/domain extraction
feature. These extend (but do not replace) the existing crawler models.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class ConfigurationNode(BaseModel):
    """A single key/value extracted from an application config file.

    Sources include appsettings.json, appsettings.{env}.json,
    launchSettings.json, web.config, app.config, and environment-variable
    references found inside any of those.
    """
    key: str                                  # dotted key path, e.g. "ConnectionStrings.Default"
    value: str = ""                           # raw string value (placeholders kept verbatim)
    source_file: str = ""                     # absolute or project-relative path
    environment: str = ""                     # "", "Development", "Staging", "Production", ...
    project: str = ""                         # owning .csproj name, if known
    kind: str = "setting"                     # setting | connection_string | feature_flag | env_var | url
    references_env_var: Optional[str] = None  # captured if value uses ${ENV:Foo} / %FOO% / $env:FOO


class DIRegistration(BaseModel):
    """A dependency-injection container registration discovered in
    Startup.cs / Program.cs / *.cs Add* extension methods."""
    project: str = ""
    source_file: str = ""
    line: int = 0
    method: str = ""           # AddSingleton | AddScoped | AddTransient | AddHttpClient | AddDbContext | AddMediatR | ...
    service_type: str = ""     # interface (e.g. IInvoiceRepository)
    implementation: str = ""   # concrete (e.g. InvoiceRepository) — may be empty for AddHttpClient/named clients
    named_client: str = ""     # for AddHttpClient("Service")
    raw: str = ""              # raw matched call snippet, trimmed


class CodeSymbol(BaseModel):
    """Lightweight C# symbol record extracted from source files.

    Captures classes, interfaces, records and the attributes/base types
    that drive cross-cutting analysis (DDD aggregates, domain events,
    REST controllers, etc.)
    """
    name: str
    kind: str                              # class | interface | record | struct | enum
    namespace: str = ""
    project: str = ""
    file: str = ""
    line: int = 0
    base_types: List[str] = Field(default_factory=list)
    attributes: List[str] = Field(default_factory=list)
    is_aggregate_root: bool = False
    is_domain_event: bool = False
    is_value_object: bool = False
    is_repository: bool = False
    is_controller: bool = False


class DomainContract(BaseModel):
    """A directed contract between two services / projects / domains.

    Inferred by joining DIRegistrations (named HTTP clients, gRPC clients,
    consumers) with ConfigurationNodes (the URL the client points to).
    """
    source_project: str = ""
    source_domain: str = ""
    target_service: str = ""        # e.g. named HTTP client name OR resolved hostname
    target_domain: str = ""         # filled in by domain_mapper
    transport: str = "http"         # http | grpc | rabbitmq | redis | s3 | unknown
    interface: str = ""             # contract interface / message type
    config_url: str = ""            # if joined with config_analyzer
    registration_file: str = ""
    registration_line: int = 0


class BusinessDomain(BaseModel):
    """A business / bounded-context domain inferred from the codebase.

    Built by clustering projects, namespaces and aggregate roots. Drives
    cross-domain integration analysis and feeds the RAG store as
    `chunk_type=business_domain`.
    """
    name: str
    description: str = ""
    projects: List[str] = Field(default_factory=list)
    namespaces: List[str] = Field(default_factory=list)
    aggregates: List[str] = Field(default_factory=list)
    domain_events: List[str] = Field(default_factory=list)
    endpoints: List[str] = Field(default_factory=list)
    inbound_contracts: List[str] = Field(default_factory=list)   # other domains that call us
    outbound_contracts: List[str] = Field(default_factory=list)  # domains we call
