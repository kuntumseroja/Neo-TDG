namespace CoreTax.Domain.Enums;

public enum AuditStatus
{
    Scheduled,
    NotificationSent,
    DocumentCollection,
    InProgress,
    FindingsReview,
    Completed,
    Appealed,
    Closed
}
