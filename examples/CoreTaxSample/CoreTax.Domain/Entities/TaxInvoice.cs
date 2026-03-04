using CoreTax.Domain.Enums;

namespace CoreTax.Domain.Entities;

public class TaxInvoice
{
    public Guid InvoiceId { get; set; }
    public string InvoiceNumber { get; set; } = string.Empty;
    public string SellerNpwp { get; set; } = string.Empty;
    public string SellerName { get; set; } = string.Empty;
    public string BuyerNpwp { get; set; } = string.Empty;
    public string BuyerName { get; set; } = string.Empty;
    public decimal TaxableAmount { get; set; }
    public decimal VatAmount { get; set; }
    public decimal LuxuryTaxAmount { get; set; }
    public InvoiceType InvoiceType { get; set; }
    public TaxStatus Status { get; set; }
    public DateTime InvoiceDate { get; set; }
    public DateTime? SubmissionDate { get; set; }
    public DateTime? ApprovalDate { get; set; }
    public string ApprovalCode { get; set; } = string.Empty;
    public string ReplacedInvoiceNumber { get; set; } = string.Empty;

    public List<TaxInvoiceItem> Items { get; set; } = new();
}

public class TaxInvoiceItem
{
    public Guid ItemId { get; set; }
    public Guid InvoiceId { get; set; }
    public string ItemName { get; set; } = string.Empty;
    public decimal Quantity { get; set; }
    public decimal UnitPrice { get; set; }
    public decimal TotalPrice { get; set; }
    public decimal DiscountAmount { get; set; }
    public decimal TaxableAmount { get; set; }
    public decimal VatAmount { get; set; }
}

public enum InvoiceType
{
    Standard,
    Replacement,
    Cancellation,
    Return
}
