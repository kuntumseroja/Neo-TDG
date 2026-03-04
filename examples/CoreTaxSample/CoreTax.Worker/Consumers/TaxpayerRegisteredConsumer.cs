using MassTransit;
using CoreTax.Contracts.Events;

namespace CoreTax.Worker.Consumers;

public class TaxpayerRegisteredConsumer : IConsumer<TaxpayerRegisteredEvent>
{
    private readonly ILogger<TaxpayerRegisteredConsumer> _logger;

    public TaxpayerRegisteredConsumer(ILogger<TaxpayerRegisteredConsumer> logger)
    {
        _logger = logger;
    }

    public async Task Consume(ConsumeContext<TaxpayerRegisteredEvent> context)
    {
        var message = context.Message;
        _logger.LogInformation("New taxpayer registered: {Npwp} - {Name}", message.Npwp, message.Name);

        // Send welcome email
        // Create default tax profile
        // Register with regional KPP office
        // Initialize compliance tracking
        await Task.Delay(300);

        _logger.LogInformation("Taxpayer onboarding completed for {Npwp}", message.Npwp);
    }
}
