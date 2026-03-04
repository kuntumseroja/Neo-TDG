namespace CoreTax.Contracts.Events;

public record TaxpayerRegisteredEvent(
    Guid TaxpayerId,
    string Npwp,
    string Name,
    string TaxpayerType,
    DateTime RegisteredAt
);
