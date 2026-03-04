using Hangfire;

namespace CoreTax.Worker.Jobs;

public class HangfireJobScheduler
{
    public void ConfigureRecurringJobs()
    {
        RecurringJob.AddOrUpdate<TaxComputationService>("daily-tax-computation", x => x.ComputeDailyTaxSummary(), Cron.Daily);

        RecurringJob.AddOrUpdate<ComplianceReportService>("monthly-compliance-report", x => x.GenerateMonthlyReport(), "0 6 1 * *");

        RecurringJob.AddOrUpdate<InvoiceReconciliationService>("hourly-invoice-reconciliation", x => x.ReconcileInvoices(), Cron.Hourly);

        BackgroundJob.Enqueue<NotificationService>(x => x.SendPendingNotifications());

        BackgroundJob.Schedule<AuditReminderService>(x => x.SendReminder(), TimeSpan.FromHours(24));
    }
}

public class TaxComputationService
{
    public void ComputeDailyTaxSummary() { }
}

public class ComplianceReportService
{
    public void GenerateMonthlyReport() { }
}

public class InvoiceReconciliationService
{
    public void ReconcileInvoices() { }
}

public class NotificationService
{
    public void SendPendingNotifications() { }
}

public class AuditReminderService
{
    public void SendReminder() { }
}
