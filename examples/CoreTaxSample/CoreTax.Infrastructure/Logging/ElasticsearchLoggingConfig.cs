using Serilog;
using Serilog.Sinks.Elasticsearch;

namespace CoreTax.Infrastructure.Logging;

public static class ElasticsearchLoggingConfig
{
    public static IHostBuilder UseCoreTaxLogging(this IHostBuilder hostBuilder)
    {
        return hostBuilder.UseSerilog((context, configuration) =>
        {
            var elasticUri = context.Configuration["Elasticsearch:Uri"] ?? "http://localhost:9200";
            var indexFormat = context.Configuration["Elasticsearch:IndexFormat"] ?? "coretax-logs-{0:yyyy.MM.dd}";

            configuration
                .ReadFrom.Configuration(context.Configuration)
                .Enrich.FromLogContext()
                .Enrich.WithMachineName()
                .Enrich.WithEnvironmentName()
                .Enrich.WithProperty("Application", "CoreTax")
                .WriteTo.Console()
                .WriteTo.Elasticsearch(new ElasticsearchSinkOptions(new Uri(elasticUri))
                {
                    AutoRegisterTemplate = true,
                    AutoRegisterTemplateVersion = AutoRegisterTemplateVersion.ESv7,
                    IndexFormat = indexFormat,
                    NumberOfReplicas = 1,
                    NumberOfShards = 2,
                    EmitEventFailure = EmitEventFailureHandling.WriteToSelfLog,
                    FailureCallback = e => Console.Error.WriteLine($"Failed to submit log event: {e.MessageTemplate}"),
                    BufferBaseFilename = "./logs/elastic-buffer",
                    BufferFileSizeLimitBytes = 5242880,
                    BatchPostingLimit = 50,
                    Period = TimeSpan.FromSeconds(2)
                });
        });
    }
}
