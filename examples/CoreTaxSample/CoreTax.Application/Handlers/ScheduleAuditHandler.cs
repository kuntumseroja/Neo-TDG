using MediatR;
using MassTransit;
using CoreTax.Application.Commands;
using CoreTax.Domain.Entities;
using CoreTax.Domain.Enums;
using CoreTax.Contracts.Events;

namespace CoreTax.Application.Handlers;

public class ScheduleAuditHandler : IRequestHandler<ScheduleAuditCommand, ScheduleAuditResult>
{
    private readonly IAuditRepository _repository;
    private readonly IPublishEndpoint _publishEndpoint;
    private readonly ILogger<ScheduleAuditHandler> _logger;

    public ScheduleAuditHandler(
        IAuditRepository repository,
        IPublishEndpoint publishEndpoint,
        ILogger<ScheduleAuditHandler> logger)
    {
        _repository = repository;
        _publishEndpoint = publishEndpoint;
        _logger = logger;
    }

    public async Task<ScheduleAuditResult> Handle(
        ScheduleAuditCommand request,
        CancellationToken cancellationToken)
    {
        _logger.LogInformation("Scheduling audit for taxpayer {Npwp}, year {AuditYear}",
            request.Npwp, request.AuditYear);

        var audit = new TaxAudit
        {
            AuditId = Guid.NewGuid(),
            Npwp = request.Npwp,
            AuditorId = request.AuditorId,
            SupervisorId = request.SupervisorId,
            AuditYear = request.AuditYear,
            Status = AuditStatus.Scheduled,
            ScheduledDate = request.ScheduledDate
        };

        await _repository.AddAsync(audit);
        await _repository.SaveChangesAsync(cancellationToken);

        await _publishEndpoint.Publish<AuditScheduledEvent>(
            new AuditScheduledEvent(
                audit.AuditId, audit.Npwp, request.AuditType,
                audit.AuditYear, audit.AuditorId, audit.ScheduledDate
            ),
            cancellationToken
        );

        return new ScheduleAuditResult
        {
            AuditId = audit.AuditId,
            AuditorName = audit.AuditorName,
            ScheduledDate = audit.ScheduledDate
        };
    }
}
