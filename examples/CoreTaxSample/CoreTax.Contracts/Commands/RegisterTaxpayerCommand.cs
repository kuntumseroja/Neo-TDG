namespace CoreTax.Contracts.Commands;

public record RegisterTaxpayerCommand(
    Guid TaxpayerId,
    string Npwp,
    string Name,
    string Address,
    string Email,
    string PhoneNumber,
    string TaxpayerType,
    string KppCode
);
