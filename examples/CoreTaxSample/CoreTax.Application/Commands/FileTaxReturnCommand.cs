using MediatR;

namespace CoreTax.Application.Commands;

public class FileTaxReturnCommand : IRequest<FileTaxReturnResult>
{
    public string Npwp { get; set; } = string.Empty;
    public string TaxPeriod { get; set; } = string.Empty;
    public int TaxYear { get; set; }
    public string ReturnType { get; set; } = string.Empty;
    public decimal GrossIncome { get; set; }
    public decimal Deductions { get; set; }
    public decimal TaxCredits { get; set; }
}

public class FileTaxReturnResult
{
    public Guid SptId { get; set; }
    public decimal TaxDue { get; set; }
    public decimal Overpayment { get; set; }
    public DateTime FilingDate { get; set; }
}
