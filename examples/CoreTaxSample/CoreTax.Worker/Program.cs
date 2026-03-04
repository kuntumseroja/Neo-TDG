using MassTransit;
using Hangfire;
using Hangfire.SqlServer;
using CoreTax.Worker.Consumers;
using CoreTax.Worker.Jobs;
using CoreTax.Worker.Services;
using CoreTax.Worker.Sagas;

var host = Host.CreateDefaultBuilder(args)
    .ConfigureServices((context, services) =>
    {
        // MassTransit with RabbitMQ
        services.AddMassTransit(x =>
        {
            x.AddConsumer<InvoiceSubmittedConsumer>();
            x.AddConsumer<TaxpayerRegisteredConsumer>();
            x.AddConsumer<PaymentReceivedConsumer>();
            x.AddConsumer<TaxReturnFiledConsumer>();
            x.AddConsumer<AuditScheduledConsumer>();

            x.AddSagaStateMachine<InvoiceApprovalSaga, InvoiceApprovalState>()
                .InMemoryRepository();

            x.UsingRabbitMq((ctx, cfg) =>
            {
                cfg.Host(context.Configuration["RabbitMQ:Host"] ?? "localhost", "/", h =>
                {
                    h.Username(context.Configuration["RabbitMQ:Username"] ?? "guest");
                    h.Password(context.Configuration["RabbitMQ:Password"] ?? "guest");
                });

                cfg.ConfigureEndpoints(ctx);
            });
        });

        // Hangfire
        services.AddHangfire(config =>
            config.SetDataCompatibilityLevel(CompatibilityLevel.Version_180)
                .UseSimpleAssemblyNameTypeSerializer()
                .UseRecommendedSerializerSettings()
                .UseSqlServerStorage(context.Configuration.GetConnectionString("HangfireConnection"))
        );
        services.AddHangfireServer();

        // Background services
        services.AddHostedService<TaxComputationBackgroundService>();
        services.AddHostedService<InvoiceExpirationHostedService>();
    })
    .Build();

// Configure Hangfire recurring jobs
using (var scope = host.Services.CreateScope())
{
    var jobScheduler = new HangfireJobScheduler();
    jobScheduler.ConfigureRecurringJobs();
}

await host.RunAsync();
