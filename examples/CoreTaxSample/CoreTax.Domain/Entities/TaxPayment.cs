using CoreTax.Domain.Enums;

namespace CoreTax.Domain.Entities;

public class TaxPayment
{
    public Guid PaymentId { get; set; }
    public string Npwp { get; set; } = string.Empty;
    public string PaymentCode { get; set; } = string.Empty;
    public string BillingCode { get; set; } = string.Empty;
    public string TaxPeriod { get; set; } = string.Empty;
    public int TaxYear { get; set; }
    public string TaxType { get; set; } = string.Empty;
    public decimal Amount { get; set; }
    public decimal PenaltyAmount { get; set; }
    public decimal TotalAmount { get; set; }
    public DateTime PaymentDate { get; set; }
    public string BankCode { get; set; } = string.Empty;
    public string TransactionReference { get; set; } = string.Empty;
    public TaxStatus Status { get; set; }
    public PaymentMethod PaymentMethod { get; set; }
    public DateTime? ValidationDate { get; set; }
}

public enum PaymentMethod
{
    BankTransfer,
    VirtualAccount,
    EBilling,
    OverTheCounter,
    ATM,
    InternetBanking
}
