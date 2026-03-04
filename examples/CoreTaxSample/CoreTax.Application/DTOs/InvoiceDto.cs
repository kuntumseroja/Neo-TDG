namespace CoreTax.Application.DTOs;

public class InvoiceDto
{
    public Guid InvoiceId { get; set; }
    public string InvoiceNumber { get; set; } = string.Empty;
    public string SellerNpwp { get; set; } = string.Empty;
    public string SellerName { get; set; } = string.Empty;
    public string BuyerNpwp { get; set; } = string.Empty;
    public string BuyerName { get; set; } = string.Empty;
    public decimal TaxableAmount { get; set; }
    public decimal VatAmount { get; set; }
    public string InvoiceType { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    public DateTime InvoiceDate { get; set; }
    public string ApprovalCode { get; set; } = string.Empty;
}
