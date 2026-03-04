namespace CoreTax.Worker.Services;

public class InvoiceExpirationHostedService : IHostedService, IDisposable
{
    private readonly ILogger<InvoiceExpirationHostedService> _logger;
    private Timer? _timer;

    public InvoiceExpirationHostedService(ILogger<InvoiceExpirationHostedService> logger)
    {
        _logger = logger;
    }

    public Task StartAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("InvoiceExpirationHostedService starting");
        _timer = new Timer(CheckExpiredInvoices, null, TimeSpan.Zero, TimeSpan.FromHours(1));
        return Task.CompletedTask;
    }

    private void CheckExpiredInvoices(object? state)
    {
        _logger.LogInformation("Checking for expired invoices at {Time}", DateTimeOffset.Now);
        // Find invoices past their submission deadline
        // Mark as expired
        // Notify sellers
    }

    public Task StopAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("InvoiceExpirationHostedService stopping");
        _timer?.Change(Timeout.Infinite, 0);
        return Task.CompletedTask;
    }

    public void Dispose()
    {
        _timer?.Dispose();
    }
}
