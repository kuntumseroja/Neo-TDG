using MediatR;

namespace CoreTax.Application.Commands;

public class ProcessPaymentCommand : IRequest<ProcessPaymentResult>
{
    public string Npwp { get; set; } = string.Empty;
    public string BillingCode { get; set; } = string.Empty;
    public string TaxPeriod { get; set; } = string.Empty;
    public int TaxYear { get; set; }
    public string TaxType { get; set; } = string.Empty;
    public decimal Amount { get; set; }
    public decimal PenaltyAmount { get; set; }
    public string PaymentMethod { get; set; } = string.Empty;
    public string BankCode { get; set; } = string.Empty;
}

public class ProcessPaymentResult
{
    public Guid PaymentId { get; set; }
    public string PaymentCode { get; set; } = string.Empty;
    public string TransactionReference { get; set; } = string.Empty;
    public DateTime PaymentDate { get; set; }
}
