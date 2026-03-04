using CoreTax.Domain.Enums;

namespace CoreTax.Domain.Entities;

public class TaxReturn
{
    public Guid SptId { get; set; }
    public string Npwp { get; set; } = string.Empty;
    public string TaxPeriod { get; set; } = string.Empty;
    public int TaxYear { get; set; }
    public ReturnType ReturnType { get; set; }
    public decimal GrossIncome { get; set; }
    public decimal Deductions { get; set; }
    public decimal TaxableIncome { get; set; }
    public decimal TotalTax { get; set; }
    public decimal TaxCredits { get; set; }
    public decimal TaxDue { get; set; }
    public decimal Overpayment { get; set; }
    public TaxStatus Status { get; set; }
    public DateTime? FilingDate { get; set; }
    public DateTime DueDate { get; set; }
    public bool IsAmended { get; set; }
    public int AmendmentNumber { get; set; }
}

public enum ReturnType
{
    SPT_1770,       // Individual annual
    SPT_1770S,      // Individual simplified
    SPT_1770SS,     // Individual very simplified
    SPT_1771,       // Corporate annual
    SPT_Masa_PPh21, // Monthly employee withholding
    SPT_Masa_PPN    // Monthly VAT
}
