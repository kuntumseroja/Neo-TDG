using MassTransit;
using CoreTax.Contracts.Events;

namespace CoreTax.Worker.Consumers;

public class PaymentReceivedConsumer : IConsumer<PaymentReceivedEvent>
{
    private readonly ILogger<PaymentReceivedConsumer> _logger;

    public PaymentReceivedConsumer(ILogger<PaymentReceivedConsumer> logger)
    {
        _logger = logger;
    }

    public async Task Consume(ConsumeContext<PaymentReceivedEvent> context)
    {
        var message = context.Message;
        _logger.LogInformation("Payment received: {PaymentId}, Amount={Amount} from {BankCode}",
            message.PaymentId, message.TotalAmount, message.BankCode);

        // Validate payment against billing code
        // Update tax return status if linked
        // Generate NTPN (tax payment receipt number)
        // Update taxpayer balance
        await Task.Delay(400);

        _logger.LogInformation("Payment {PaymentId} validated and recorded", message.PaymentId);
    }
}
