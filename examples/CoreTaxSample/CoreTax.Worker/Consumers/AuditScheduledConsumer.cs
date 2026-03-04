using MassTransit;
using CoreTax.Contracts.Events;

namespace CoreTax.Worker.Consumers;

public class AuditScheduledConsumer : IConsumer<AuditScheduledEvent>
{
    private readonly ILogger<AuditScheduledConsumer> _logger;

    public AuditScheduledConsumer(ILogger<AuditScheduledConsumer> logger)
    {
        _logger = logger;
    }

    public async Task Consume(ConsumeContext<AuditScheduledEvent> context)
    {
        var message = context.Message;
        _logger.LogInformation("Audit scheduled: {AuditId} for {Npwp}, Year={Year}, Auditor={Auditor}",
            message.AuditId, message.Npwp, message.AuditYear, message.AuditorId);

        // Prepare audit document package
        // Notify taxpayer via registered email
        // Assign audit team resources
        // Create audit workspace
        await Task.Delay(300);

        _logger.LogInformation("Audit {AuditId} preparation completed", message.AuditId);
    }
}
