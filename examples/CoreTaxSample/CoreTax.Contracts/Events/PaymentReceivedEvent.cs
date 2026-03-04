namespace CoreTax.Contracts.Events;

public record PaymentReceivedEvent(
    Guid PaymentId,
    string Npwp,
    string BillingCode,
    decimal TotalAmount,
    string BankCode,
    DateTime PaidAt
);
