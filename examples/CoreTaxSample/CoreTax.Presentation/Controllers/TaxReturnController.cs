using MediatR;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using CoreTax.Application.Commands;
using CoreTax.Application.Queries;

namespace CoreTax.Presentation.Controllers;

[Route("api/v1/tax-returns")]
[ApiController]
[Authorize]
public class TaxReturnController : ControllerBase
{
    private readonly IMediator _mediator;
    private readonly ILogger<TaxReturnController> _logger;

    public TaxReturnController(IMediator mediator, ILogger<TaxReturnController> logger)
    {
        _mediator = mediator;
        _logger = logger;
    }

    [HttpPost("file")]
    public async Task<IActionResult> FileTaxReturn([FromBody] FileTaxReturnCommand command)
    {
        _logger.LogInformation("Filing tax return for {Npwp}, period {Period}/{Year}",
            command.Npwp, command.TaxPeriod, command.TaxYear);
        var result = await _mediator.Send(command);
        return Accepted(result);
    }

    [HttpGet("{sptId}")]
    public async Task<IActionResult> GetTaxReturn(Guid sptId)
    {
        var result = await _mediator.Send(new GetTaxReturnStatusQuery { SptId = sptId });
        if (result == null) return NotFound();
        return Ok(result);
    }

    [HttpGet("status/{npwp}")]
    public async Task<IActionResult> GetTaxReturnStatus(string npwp, [FromQuery] int? year)
    {
        var result = await _mediator.Send(new GetTaxReturnStatusQuery { Npwp = npwp });
        return Ok(result);
    }
}
