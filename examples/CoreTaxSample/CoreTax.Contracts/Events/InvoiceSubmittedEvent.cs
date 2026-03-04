namespace CoreTax.Contracts.Events;

public record InvoiceSubmittedEvent(
    Guid InvoiceId,
    string InvoiceNumber,
    string SellerNpwp,
    string BuyerNpwp,
    decimal TaxableAmount,
    decimal VatAmount,
    DateTime SubmittedAt
);
