using MediatR;
using MassTransit;
using CoreTax.Application.Commands;
using CoreTax.Domain.Entities;
using CoreTax.Domain.Enums;
using CoreTax.Contracts.Events;

namespace CoreTax.Application.Handlers;

public class SubmitInvoiceHandler : IRequestHandler<SubmitInvoiceCommand, SubmitInvoiceResult>
{
    private readonly IInvoiceRepository _repository;
    private readonly IPublishEndpoint _publishEndpoint;
    private readonly ILogger<SubmitInvoiceHandler> _logger;

    public SubmitInvoiceHandler(
        IInvoiceRepository repository,
        IPublishEndpoint publishEndpoint,
        ILogger<SubmitInvoiceHandler> logger)
    {
        _repository = repository;
        _publishEndpoint = publishEndpoint;
        _logger = logger;
    }

    public async Task<SubmitInvoiceResult> Handle(
        SubmitInvoiceCommand request,
        CancellationToken cancellationToken)
    {
        _logger.LogInformation("Submitting invoice {InvoiceNumber} from seller {SellerNpwp}",
            request.InvoiceNumber, request.SellerNpwp);

        var invoice = new TaxInvoice
        {
            InvoiceId = Guid.NewGuid(),
            InvoiceNumber = request.InvoiceNumber,
            SellerNpwp = request.SellerNpwp,
            BuyerNpwp = request.BuyerNpwp,
            TaxableAmount = request.TaxableAmount,
            VatAmount = request.VatAmount,
            InvoiceDate = request.InvoiceDate,
            SubmissionDate = DateTime.UtcNow,
            Status = TaxStatus.Submitted,
            ApprovalCode = GenerateApprovalCode()
        };

        await _repository.AddAsync(invoice);
        await _repository.SaveChangesAsync(cancellationToken);

        await _publishEndpoint.Publish<InvoiceSubmittedEvent>(
            new InvoiceSubmittedEvent(
                invoice.InvoiceId,
                invoice.InvoiceNumber,
                invoice.SellerNpwp,
                invoice.BuyerNpwp,
                invoice.TaxableAmount,
                invoice.VatAmount,
                DateTime.UtcNow
            ),
            cancellationToken
        );

        return new SubmitInvoiceResult
        {
            InvoiceId = invoice.InvoiceId,
            ApprovalCode = invoice.ApprovalCode,
            SubmissionDate = invoice.SubmissionDate.Value
        };
    }

    private string GenerateApprovalCode() =>
        $"APV-{DateTime.UtcNow:yyyyMMdd}-{Guid.NewGuid().ToString()[..8].ToUpper()}";
}
