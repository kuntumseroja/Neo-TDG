using MediatR;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using CoreTax.Application.Commands;

namespace CoreTax.Presentation.Controllers;

[Route("api/v1/audits")]
[ApiController]
[Authorize]
public class AuditController : ControllerBase
{
    private readonly IMediator _mediator;
    private readonly ILogger<AuditController> _logger;

    public AuditController(IMediator mediator, ILogger<AuditController> logger)
    {
        _mediator = mediator;
        _logger = logger;
    }

    [HttpPost("schedule")]
    public async Task<IActionResult> ScheduleAudit([FromBody] ScheduleAuditCommand command)
    {
        _logger.LogInformation("Scheduling audit for {Npwp}, year {Year}", command.Npwp, command.AuditYear);
        var result = await _mediator.Send(command);
        return Accepted(result);
    }

    [HttpGet("{auditId}")]
    public async Task<IActionResult> GetAudit(Guid auditId)
    {
        return Ok(new { AuditId = auditId });
    }

    [HttpPut("{auditId}/complete")]
    public async Task<IActionResult> CompleteAudit(Guid auditId, [FromBody] CompleteAuditRequest request)
    {
        _logger.LogInformation("Completing audit: {AuditId}", auditId);
        return Ok(new { AuditId = auditId, Status = "Completed" });
    }

    [HttpGet("by-taxpayer/{npwp}")]
    public async Task<IActionResult> GetAuditsByTaxpayer(string npwp)
    {
        return Ok(new { Npwp = npwp, Audits = new List<object>() });
    }
}

public record CompleteAuditRequest(decimal FindingsAmount, decimal PenaltyAmount, string Notes);
