using Serilog;
using Serilog.Sinks.Elasticsearch;

namespace CoreTax.Shared.Logging;

public static class SerilogConfiguration
{
    public static void ConfigureLogging(IConfiguration configuration)
    {
        var elasticUri = configuration["Elasticsearch:Uri"] ?? "http://localhost:9200";

        Log.Logger = new LoggerConfiguration()
            .ReadFrom.Configuration(configuration)
            .Enrich.FromLogContext()
            .Enrich.WithProperty("Application", "CoreTax")
            .Enrich.WithProperty("Environment", Environment.GetEnvironmentVariable("ASPNETCORE_ENVIRONMENT") ?? "Production")
            .WriteTo.Console(outputTemplate: "[{Timestamp:HH:mm:ss} {Level:u3}] {Message:lj} {Properties:j}{NewLine}{Exception}")
            .WriteTo.Elasticsearch(new ElasticsearchSinkOptions(new Uri(elasticUri))
            {
                AutoRegisterTemplate = true,
                IndexFormat = "coretax-{0:yyyy.MM.dd}",
                NumberOfReplicas = 1
            })
            .CreateLogger();
    }
}
