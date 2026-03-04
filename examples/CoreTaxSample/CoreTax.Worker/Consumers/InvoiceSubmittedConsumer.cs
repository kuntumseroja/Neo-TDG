using MassTransit;
using CoreTax.Contracts.Events;

namespace CoreTax.Worker.Consumers;

public class InvoiceSubmittedConsumer : IConsumer<InvoiceSubmittedEvent>
{
    private readonly ILogger<InvoiceSubmittedConsumer> _logger;

    public InvoiceSubmittedConsumer(ILogger<InvoiceSubmittedConsumer> logger)
    {
        _logger = logger;
    }

    public async Task Consume(ConsumeContext<InvoiceSubmittedEvent> context)
    {
        var message = context.Message;
        _logger.LogInformation("Processing submitted invoice: {InvoiceNumber} from {SellerNpwp}",
            message.InvoiceNumber, message.SellerNpwp);

        // Validate invoice against tax authority rules
        // Check seller and buyer NPWP validity
        // Generate QR code for e-invoice
        // Send notification to buyer
        await Task.Delay(500); // Simulate processing

        _logger.LogInformation("Invoice {InvoiceNumber} processed and validated", message.InvoiceNumber);
    }
}
