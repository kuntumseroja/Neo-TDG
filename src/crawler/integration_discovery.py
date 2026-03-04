"""Integration point discovery (HTTP clients, Redis, Consul, S3, etc.)."""

import re
from typing import List
from src.models.crawler import IntegrationPoint

# HTTP Client patterns
_HTTPCLIENT_INJECT = re.compile(
    r"(?:IHttpClientFactory|HttpClient)\s+\w+",
)
_HTTPCLIENT_NAMED = re.compile(
    r'AddHttpClient[<(].*?"([^"]+)"',
)
_HTTPCLIENT_CALL = re.compile(
    r'(?:GetAsync|PostAsync|PutAsync|DeleteAsync|SendAsync)\s*\(\s*["\$]([^"]*)',
)

# Redis patterns
_REDIS_INJECT = re.compile(
    r"IConnectionMultiplexer|IDistributedCache|IDatabase",
)
_REDIS_OPERATION = re.compile(
    r"\.(?:StringSetAsync|StringGetAsync|HashSetAsync|KeyDeleteAsync|SubscribeAsync)\s*\(",
)

# Consul patterns
_CONSUL_INJECT = re.compile(
    r"IConsulClient|ConsulClient",
)
_CONSUL_REGISTER = re.compile(
    r"Agent\.ServiceRegister",
)

# S3 / Object storage patterns
_S3_INJECT = re.compile(
    r"IAmazonS3|AmazonS3Client|IBlobStorage|MinioClient",
)
_S3_OPERATION = re.compile(
    r"\.(?:PutObjectAsync|GetObjectAsync|DeleteObjectAsync|UploadObjectAsync|PutObject)\s*\(",
)

# gRPC patterns
_GRPC_SERVICE = re.compile(
    r"class\s+(\w+)\s*:\s*.*?\.(\w+)Base",
)
_GRPC_CLIENT = re.compile(
    r"(\w+)\.(\w+)Client",
)

# RabbitMQ direct (non-MassTransit)
_RABBITMQ_DIRECT = re.compile(
    r"IConnection|ConnectionFactory|BasicPublish|BasicConsume|QueueDeclare",
)


def discover_integrations(content: str, file_path: str) -> List[IntegrationPoint]:
    """Discover integration points in a C# file."""
    results = []

    # Infer source service from file path
    source_service = _infer_service(file_path)

    # HTTP clients
    if _HTTPCLIENT_INJECT.search(content):
        named_clients = _HTTPCLIENT_NAMED.findall(content)
        urls = _HTTPCLIENT_CALL.findall(content)

        for client_name in named_clients:
            results.append(IntegrationPoint(
                type="http",
                source_service=source_service,
                target=client_name,
                contract="HttpClient",
                file=file_path,
            ))

        for url in urls:
            if url and not url.startswith("{"):
                results.append(IntegrationPoint(
                    type="http",
                    source_service=source_service,
                    target=url[:100],
                    contract="HTTP call",
                    file=file_path,
                ))

        if not named_clients and not urls:
            results.append(IntegrationPoint(
                type="http",
                source_service=source_service,
                target="external-service",
                contract="HttpClient",
                file=file_path,
            ))

    # Redis
    if _REDIS_INJECT.search(content):
        results.append(IntegrationPoint(
            type="redis",
            source_service=source_service,
            target="redis",
            contract="IDistributedCache/IConnectionMultiplexer",
            file=file_path,
        ))

    # Consul
    if _CONSUL_INJECT.search(content):
        target = "consul-discovery"
        if _CONSUL_REGISTER.search(content):
            target = "consul-registration"
        results.append(IntegrationPoint(
            type="consul",
            source_service=source_service,
            target=target,
            contract="IConsulClient",
            file=file_path,
        ))

    # S3 / Object storage
    if _S3_INJECT.search(content):
        results.append(IntegrationPoint(
            type="s3",
            source_service=source_service,
            target="object-storage",
            contract="IAmazonS3/IBlobStorage",
            file=file_path,
        ))

    # gRPC services
    for match in _GRPC_SERVICE.finditer(content):
        results.append(IntegrationPoint(
            type="grpc",
            source_service=source_service,
            target=match.group(2),
            contract=f"gRPC service: {match.group(1)}",
            file=file_path,
        ))
    for match in _GRPC_CLIENT.finditer(content):
        results.append(IntegrationPoint(
            type="grpc",
            source_service=source_service,
            target=match.group(1),
            contract=f"gRPC client: {match.group(2)}Client",
            file=file_path,
        ))

    # Direct RabbitMQ (non-MassTransit)
    if _RABBITMQ_DIRECT.search(content):
        results.append(IntegrationPoint(
            type="rabbitmq",
            source_service=source_service,
            target="rabbitmq-direct",
            contract="IConnection/ConnectionFactory",
            file=file_path,
        ))

    return results


def _infer_service(file_path: str) -> str:
    """Infer service name from file path."""
    parts = file_path.replace("\\", "/").split("/")
    # Look for project-like directory names
    for part in parts:
        if "." in part and not part.endswith(".cs"):
            return part
    return parts[-2] if len(parts) >= 2 else "unknown"
