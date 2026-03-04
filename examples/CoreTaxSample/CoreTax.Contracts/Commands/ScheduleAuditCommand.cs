namespace CoreTax.Contracts.Commands;

public record ScheduleAuditCommand(
    Guid AuditId,
    string Npwp,
    string AuditType,
    int AuditYear,
    string AuditorId,
    string SupervisorId,
    DateTime ScheduledDate
);
