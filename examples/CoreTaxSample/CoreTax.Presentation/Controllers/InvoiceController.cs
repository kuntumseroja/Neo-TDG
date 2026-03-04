using MediatR;
using MassTransit;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using CoreTax.Application.Commands;
using CoreTax.Application.Queries;
using CoreTax.Contracts.Events;

namespace CoreTax.Presentation.Controllers;

[Route("api/v1/invoices")]
[ApiController]
[Authorize]
public class InvoiceController : ControllerBase
{
    private readonly IMediator _mediator;
    private readonly IPublishEndpoint _publishEndpoint;
    private readonly ILogger<InvoiceController> _logger;

    public InvoiceController(
        IMediator mediator,
        IPublishEndpoint publishEndpoint,
        ILogger<InvoiceController> logger)
    {
        _mediator = mediator;
        _publishEndpoint = publishEndpoint;
        _logger = logger;
    }

    [HttpPost("submit")]
    public async Task<IActionResult> SubmitInvoice([FromBody] SubmitInvoiceCommand command)
    {
        _logger.LogInformation("Invoice submission: {InvoiceNumber}", command.InvoiceNumber);
        var result = await _mediator.Send(command);
        return Accepted(result);
    }

    [HttpGet("{invoiceNumber}")]
    public async Task<IActionResult> GetInvoice(string invoiceNumber)
    {
        var query = new GetInvoicesByPeriodQuery { Npwp = invoiceNumber };
        var result = await _mediator.Send(query);
        return Ok(result);
    }

    [HttpPut("{invoiceNumber}/approve")]
    public async Task<IActionResult> ApproveInvoice(string invoiceNumber)
    {
        _logger.LogInformation("Approving invoice: {InvoiceNumber}", invoiceNumber);
        // Approval logic via mediator
        return Ok(new { InvoiceNumber = invoiceNumber, Status = "Approved" });
    }

    [HttpDelete("{invoiceNumber}")]
    public async Task<IActionResult> CancelInvoice(string invoiceNumber)
    {
        _logger.LogInformation("Cancelling invoice: {InvoiceNumber}", invoiceNumber);
        return Ok(new { InvoiceNumber = invoiceNumber, Status = "Cancelled" });
    }
}
