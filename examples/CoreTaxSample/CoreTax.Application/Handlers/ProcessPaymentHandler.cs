using MediatR;
using MassTransit;
using CoreTax.Application.Commands;
using CoreTax.Domain.Entities;
using CoreTax.Domain.Enums;
using CoreTax.Contracts.Events;

namespace CoreTax.Application.Handlers;

public class ProcessPaymentHandler : IRequestHandler<ProcessPaymentCommand, ProcessPaymentResult>
{
    private readonly IPaymentRepository _repository;
    private readonly ISendEndpointProvider _sendEndpointProvider;
    private readonly IPublishEndpoint _publishEndpoint;
    private readonly ILogger<ProcessPaymentHandler> _logger;

    public ProcessPaymentHandler(
        IPaymentRepository repository,
        ISendEndpointProvider sendEndpointProvider,
        IPublishEndpoint publishEndpoint,
        ILogger<ProcessPaymentHandler> logger)
    {
        _repository = repository;
        _sendEndpointProvider = sendEndpointProvider;
        _publishEndpoint = publishEndpoint;
        _logger = logger;
    }

    public async Task<ProcessPaymentResult> Handle(
        ProcessPaymentCommand request,
        CancellationToken cancellationToken)
    {
        _logger.LogInformation("Processing payment for billing code: {BillingCode}", request.BillingCode);

        var payment = new TaxPayment
        {
            PaymentId = Guid.NewGuid(),
            Npwp = request.Npwp,
            BillingCode = request.BillingCode,
            PaymentCode = GeneratePaymentCode(),
            TaxPeriod = request.TaxPeriod,
            TaxYear = request.TaxYear,
            TaxType = request.TaxType,
            Amount = request.Amount,
            PenaltyAmount = request.PenaltyAmount,
            TotalAmount = request.Amount + request.PenaltyAmount,
            PaymentDate = DateTime.UtcNow,
            BankCode = request.BankCode,
            TransactionReference = Guid.NewGuid().ToString("N")[..16].ToUpper(),
            Status = TaxStatus.Paid
        };

        await _repository.AddAsync(payment);
        await _repository.SaveChangesAsync(cancellationToken);

        await _publishEndpoint.Publish<PaymentReceivedEvent>(
            new PaymentReceivedEvent(
                payment.PaymentId, payment.Npwp, payment.BillingCode,
                payment.TotalAmount, payment.BankCode, DateTime.UtcNow
            ),
            cancellationToken
        );

        return new ProcessPaymentResult
        {
            PaymentId = payment.PaymentId,
            PaymentCode = payment.PaymentCode,
            TransactionReference = payment.TransactionReference,
            PaymentDate = payment.PaymentDate
        };
    }

    private string GeneratePaymentCode() =>
        $"NTPN-{DateTime.UtcNow:yyyyMMddHHmmss}-{new Random().Next(1000, 9999)}";
}
