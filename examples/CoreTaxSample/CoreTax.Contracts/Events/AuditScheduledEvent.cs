namespace CoreTax.Contracts.Events;

public record AuditScheduledEvent(
    Guid AuditId,
    string Npwp,
    string AuditType,
    int AuditYear,
    string AuditorId,
    DateTime ScheduledDate
);
