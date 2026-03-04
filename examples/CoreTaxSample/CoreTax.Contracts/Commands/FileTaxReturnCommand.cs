namespace CoreTax.Contracts.Commands;

public record FileTaxReturnCommand(
    Guid SptId,
    string Npwp,
    string TaxPeriod,
    int TaxYear,
    string ReturnType,
    decimal GrossIncome,
    decimal Deductions,
    decimal TaxableIncome,
    decimal TotalTax,
    decimal TaxCredits
);
