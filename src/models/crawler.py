"""Solution crawler data models."""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime

from src.models.domain import (
    ConfigurationNode,
    DIRegistration,
    CodeSymbol,
    DomainContract,
    BusinessDomain,
)


class PackageRef(BaseModel):
    """NuGet or npm package reference."""
    name: str
    version: str = ""


class ProjectInfo(BaseModel):
    """Information about a single project within a solution."""
    name: str
    path: str
    layer: str = ""  # Domain|Application|Infrastructure|Presentation|Tests|Shared
    framework: str = ""
    references: List[str] = Field(default_factory=list)  # Inter-project references
    nuget_packages: List[PackageRef] = Field(default_factory=list)
    # Deep-analysis additions (populated only when crawler.deep_analysis.enabled)
    configurations: List[ConfigurationNode] = Field(default_factory=list)
    di_registrations: List[DIRegistration] = Field(default_factory=list)
    code_symbols: List[CodeSymbol] = Field(default_factory=list)


class EndpointInfo(BaseModel):
    """HTTP API endpoint discovered in a controller."""
    route: str
    method: str  # GET|POST|PUT|DELETE|PATCH
    controller: str
    file: str
    line: int = 0
    auth_required: bool = False
    request_model: str = ""
    response_model: str = ""


class ConsumerInfo(BaseModel):
    """MassTransit/RabbitMQ consumer."""
    consumer_class: str
    message_type: str
    queue: str = ""
    file: str = ""


class SchedulerInfo(BaseModel):
    """Hangfire/Quartz scheduled job."""
    job_name: str
    cron_expression: str = ""
    handler_class: str = ""
    file: str = ""
    description: str = ""


class IntegrationPoint(BaseModel):
    """External integration point."""
    type: str  # rabbitmq|http|redis|grpc|consul|s3
    source_service: str = ""
    target: str = ""
    contract: str = ""
    file: str = ""


class UIComponent(BaseModel):
    """Angular UI component."""
    name: str
    selector: str = ""
    template_file: str = ""
    component_file: str = ""
    module: str = ""
    routes: List[str] = Field(default_factory=list)
    api_calls: List[str] = Field(default_factory=list)


class DataModel(BaseModel):
    """EF Core data model entity."""
    name: str
    db_context: str = ""
    properties: List[str] = Field(default_factory=list)
    relationships: List[str] = Field(default_factory=list)
    file: str = ""


class CrawlReport(BaseModel):
    """Complete report from crawling a solution."""
    solution: str
    crawled_at: datetime = Field(default_factory=datetime.utcnow)
    projects: List[ProjectInfo] = Field(default_factory=list)
    dependency_graph: Dict = Field(default_factory=dict)
    endpoints: List[EndpointInfo] = Field(default_factory=list)
    consumers: List[ConsumerInfo] = Field(default_factory=list)
    schedulers: List[SchedulerInfo] = Field(default_factory=list)
    integrations: List[IntegrationPoint] = Field(default_factory=list)
    ui_components: List[UIComponent] = Field(default_factory=list)
    data_models: List[DataModel] = Field(default_factory=list)
    configuration: Dict = Field(default_factory=dict)
    # Deep-analysis additions
    business_domains: List[BusinessDomain] = Field(default_factory=list)
    domain_contracts: List[DomainContract] = Field(default_factory=list)
