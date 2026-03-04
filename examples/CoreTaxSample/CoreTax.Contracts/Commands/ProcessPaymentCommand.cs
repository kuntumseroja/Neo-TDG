namespace CoreTax.Contracts.Commands;

public record ProcessPaymentCommand(
    Guid PaymentId,
    string Npwp,
    string BillingCode,
    string TaxPeriod,
    int TaxYear,
    string TaxType,
    decimal Amount,
    decimal PenaltyAmount,
    string PaymentMethod,
    string BankCode
);
