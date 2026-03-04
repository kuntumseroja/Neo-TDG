using MediatR;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using CoreTax.Application.Commands;

namespace CoreTax.Presentation.Controllers;

[Route("api/v1/payments")]
[ApiController]
[Authorize]
public class PaymentController : ControllerBase
{
    private readonly IMediator _mediator;
    private readonly ILogger<PaymentController> _logger;

    public PaymentController(IMediator mediator, ILogger<PaymentController> logger)
    {
        _mediator = mediator;
        _logger = logger;
    }

    [HttpPost("process")]
    public async Task<IActionResult> ProcessPayment([FromBody] ProcessPaymentCommand command)
    {
        _logger.LogInformation("Processing payment: Billing={BillingCode}, Amount={Amount}",
            command.BillingCode, command.Amount);
        var result = await _mediator.Send(command);
        return Accepted(result);
    }

    [HttpGet("{paymentId}")]
    public async Task<IActionResult> GetPayment(Guid paymentId)
    {
        return Ok(new { PaymentId = paymentId });
    }

    [HttpPost("validate")]
    public async Task<IActionResult> ValidatePayment([FromBody] ValidatePaymentRequest request)
    {
        _logger.LogInformation("Validating payment: {PaymentCode}", request.PaymentCode);
        return Ok(new { PaymentCode = request.PaymentCode, IsValid = true });
    }
}

public record ValidatePaymentRequest(string PaymentCode, string TransactionReference);
