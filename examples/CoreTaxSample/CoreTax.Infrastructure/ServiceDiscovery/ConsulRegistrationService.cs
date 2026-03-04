using Consul;

namespace CoreTax.Infrastructure.ServiceDiscovery;

public class ConsulRegistrationService : IHostedService
{
    private readonly IConsulClient _consulClient;
    private readonly ILogger<ConsulRegistrationService> _logger;
    private readonly string _serviceId;
    private readonly string _serviceName;
    private readonly string _serviceHost;
    private readonly int _servicePort;

    public ConsulRegistrationService(
        IConsulClient consulClient,
        IConfiguration configuration,
        ILogger<ConsulRegistrationService> logger)
    {
        _consulClient = consulClient;
        _logger = logger;
        _serviceName = configuration["ServiceDiscovery:ServiceName"] ?? "coretax-api";
        _serviceHost = configuration["ServiceDiscovery:Host"] ?? "localhost";
        _servicePort = int.Parse(configuration["ServiceDiscovery:Port"] ?? "5000");
        _serviceId = $"{_serviceName}-{_serviceHost}-{_servicePort}";
    }

    public async Task StartAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("Registering service {ServiceName} with Consul", _serviceName);

        var registration = new AgentServiceRegistration
        {
            ID = _serviceId,
            Name = _serviceName,
            Address = _serviceHost,
            Port = _servicePort,
            Tags = new[] { "coretax", "api", "v1" },
            Check = new AgentServiceCheck
            {
                HTTP = $"http://{_serviceHost}:{_servicePort}/health",
                Interval = TimeSpan.FromSeconds(30),
                Timeout = TimeSpan.FromSeconds(5),
                DeregisterCriticalServiceAfter = TimeSpan.FromMinutes(5)
            }
        };

        await _consulClient.Agent.ServiceRegister(registration, cancellationToken);
        _logger.LogInformation("Service {ServiceId} registered with Consul", _serviceId);
    }

    public async Task StopAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("Deregistering service {ServiceId} from Consul", _serviceId);
        await _consulClient.Agent.ServiceDeregister(_serviceId, cancellationToken);
    }

    public async Task<List<string>> GetServiceInstancesAsync(string serviceName)
    {
        var services = await _consulClient.Health.Service(serviceName, string.Empty, true);
        return services.Response
            .Select(s => $"http://{s.Service.Address}:{s.Service.Port}")
            .ToList();
    }
}
