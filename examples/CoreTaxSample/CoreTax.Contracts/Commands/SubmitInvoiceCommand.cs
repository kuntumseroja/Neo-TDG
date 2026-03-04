namespace CoreTax.Contracts.Commands;

public record SubmitInvoiceCommand(
    Guid InvoiceId,
    string InvoiceNumber,
    string SellerNpwp,
    string BuyerNpwp,
    decimal TaxableAmount,
    decimal VatAmount,
    string InvoiceType,
    DateTime InvoiceDate
);
