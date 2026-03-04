using MediatR;

namespace CoreTax.Application.Commands;

public class ScheduleAuditCommand : IRequest<ScheduleAuditResult>
{
    public string Npwp { get; set; } = string.Empty;
    public string AuditType { get; set; } = string.Empty;
    public int AuditYear { get; set; }
    public string AuditorId { get; set; } = string.Empty;
    public string SupervisorId { get; set; } = string.Empty;
    public DateTime ScheduledDate { get; set; }
}

public class ScheduleAuditResult
{
    public Guid AuditId { get; set; }
    public string AuditorName { get; set; } = string.Empty;
    public DateTime ScheduledDate { get; set; }
}
