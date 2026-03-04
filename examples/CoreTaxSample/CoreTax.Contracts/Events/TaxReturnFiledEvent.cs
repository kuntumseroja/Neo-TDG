namespace CoreTax.Contracts.Events;

public record TaxReturnFiledEvent(
    Guid SptId,
    string Npwp,
    string TaxPeriod,
    int TaxYear,
    string ReturnType,
    decimal TaxDue,
    DateTime FiledAt
);
