using MediatR;

namespace CoreTax.Application.Commands;

public class SubmitInvoiceCommand : IRequest<SubmitInvoiceResult>
{
    public string InvoiceNumber { get; set; } = string.Empty;
    public string SellerNpwp { get; set; } = string.Empty;
    public string BuyerNpwp { get; set; } = string.Empty;
    public decimal TaxableAmount { get; set; }
    public decimal VatAmount { get; set; }
    public string InvoiceType { get; set; } = "Standard";
    public DateTime InvoiceDate { get; set; }
    public List<InvoiceItemDto> Items { get; set; } = new();
}

public class InvoiceItemDto
{
    public string ItemName { get; set; } = string.Empty;
    public decimal Quantity { get; set; }
    public decimal UnitPrice { get; set; }
}

public class SubmitInvoiceResult
{
    public Guid InvoiceId { get; set; }
    public string ApprovalCode { get; set; } = string.Empty;
    public DateTime SubmissionDate { get; set; }
}
