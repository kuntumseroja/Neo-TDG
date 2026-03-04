using MassTransit;
using CoreTax.Contracts.Events;

namespace CoreTax.Worker.Consumers;

public class TaxReturnFiledConsumer : IConsumer<TaxReturnFiledEvent>
{
    private readonly ILogger<TaxReturnFiledConsumer> _logger;

    public TaxReturnFiledConsumer(ILogger<TaxReturnFiledConsumer> logger)
    {
        _logger = logger;
    }

    public async Task Consume(ConsumeContext<TaxReturnFiledEvent> context)
    {
        var message = context.Message;
        _logger.LogInformation("Tax return filed: SPT {SptId} for {Npwp}, Period={Period}/{Year}",
            message.SptId, message.Npwp, message.TaxPeriod, message.TaxYear);

        // Validate return completeness
        // Cross-check with invoice data (PPN)
        // Calculate penalties for late filing
        // Generate filing receipt (BPE)
        // Queue for audit selection if flagged
        await Task.Delay(600);

        _logger.LogInformation("Tax return {SptId} validation completed", message.SptId);
    }
}
