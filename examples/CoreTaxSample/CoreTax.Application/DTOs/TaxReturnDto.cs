namespace CoreTax.Application.DTOs;

public class TaxReturnDto
{
    public Guid SptId { get; set; }
    public string Npwp { get; set; } = string.Empty;
    public string TaxPeriod { get; set; } = string.Empty;
    public int TaxYear { get; set; }
    public string ReturnType { get; set; } = string.Empty;
    public decimal GrossIncome { get; set; }
    public decimal TaxableIncome { get; set; }
    public decimal TotalTax { get; set; }
    public decimal TaxDue { get; set; }
    public decimal Overpayment { get; set; }
    public string Status { get; set; } = string.Empty;
    public DateTime? FilingDate { get; set; }
    public bool IsAmended { get; set; }
}
