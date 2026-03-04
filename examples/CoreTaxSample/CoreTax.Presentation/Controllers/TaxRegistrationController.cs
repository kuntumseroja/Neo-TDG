using MediatR;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using CoreTax.Application.Commands;
using CoreTax.Application.Queries;

namespace CoreTax.Presentation.Controllers;

[Route("api/v1/[controller]")]
[ApiController]
[Authorize]
public class TaxRegistrationController : ControllerBase
{
    private readonly IMediator _mediator;
    private readonly ILogger<TaxRegistrationController> _logger;

    public TaxRegistrationController(IMediator mediator, ILogger<TaxRegistrationController> logger)
    {
        _mediator = mediator;
        _logger = logger;
    }

    [HttpPost("register")]
    public async Task<IActionResult> RegisterTaxpayer([FromBody] RegisterTaxpayerCommand command)
    {
        _logger.LogInformation("Registration request for NPWP: {Npwp}", command.Npwp);
        var result = await _mediator.Send(command);
        return CreatedAtAction(nameof(GetTaxpayer), new { npwp = result.Npwp }, result);
    }

    [HttpGet("{npwp}")]
    public async Task<IActionResult> GetTaxpayer(string npwp)
    {
        var result = await _mediator.Send(new GetTaxpayerByNpwpQuery { Npwp = npwp });
        if (result == null) return NotFound();
        return Ok(result);
    }

    [HttpPut("{npwp}")]
    public async Task<IActionResult> UpdateTaxpayer(string npwp, [FromBody] RegisterTaxpayerCommand command)
    {
        _logger.LogInformation("Update request for taxpayer: {Npwp}", npwp);
        var result = await _mediator.Send(command);
        return Ok(result);
    }
}
