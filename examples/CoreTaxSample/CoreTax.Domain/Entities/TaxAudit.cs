using CoreTax.Domain.Enums;

namespace CoreTax.Domain.Entities;

public class TaxAudit
{
    public Guid AuditId { get; set; }
    public string Npwp { get; set; } = string.Empty;
    public string TaxpayerName { get; set; } = string.Empty;
    public AuditType AuditType { get; set; }
    public int AuditYear { get; set; }
    public string AuditorId { get; set; } = string.Empty;
    public string AuditorName { get; set; } = string.Empty;
    public string SupervisorId { get; set; } = string.Empty;
    public AuditStatus Status { get; set; }
    public DateTime ScheduledDate { get; set; }
    public DateTime? StartDate { get; set; }
    public DateTime? EndDate { get; set; }
    public decimal FindingsAmount { get; set; }
    public decimal PenaltyAmount { get; set; }
    public string Notes { get; set; } = string.Empty;
    public List<AuditFinding> Findings { get; set; } = new();
}

public class AuditFinding
{
    public Guid FindingId { get; set; }
    public Guid AuditId { get; set; }
    public string Description { get; set; } = string.Empty;
    public string TaxType { get; set; } = string.Empty;
    public decimal UnderpaidAmount { get; set; }
    public decimal PenaltyAmount { get; set; }
}

public enum AuditType
{
    Routine,
    Special,
    Transfer,
    Refund,
    Criminal
}
