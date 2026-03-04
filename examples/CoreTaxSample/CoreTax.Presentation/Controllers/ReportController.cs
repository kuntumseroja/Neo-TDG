using Microsoft.AspNetCore.Mvc;

namespace CoreTax.Presentation.Controllers;

[Route("api/v1/reports")]
[ApiController]
public class ReportController : ControllerBase
{
    private readonly ILogger<ReportController> _logger;

    public ReportController(ILogger<ReportController> logger)
    {
        _logger = logger;
    }

    [HttpGet("revenue/{taxYear}")]
    public async Task<IActionResult> GetRevenueReport(int taxYear)
    {
        _logger.LogInformation("Generating revenue report for year {Year}", taxYear);
        return Ok(new
        {
            TaxYear = taxYear,
            TotalVatCollected = 15_500_000_000m,
            TotalIncomeTaxCollected = 22_300_000_000m,
            TotalPenalties = 1_200_000_000m,
            TaxpayerCount = 45_230
        });
    }

    [HttpGet("compliance/{taxPeriod}")]
    public async Task<IActionResult> GetComplianceReport(string taxPeriod)
    {
        _logger.LogInformation("Generating compliance report for period {Period}", taxPeriod);
        return Ok(new
        {
            TaxPeriod = taxPeriod,
            TotalFilers = 32_500,
            OnTimeFilers = 28_750,
            LateFilers = 3_750,
            ComplianceRate = 88.46
        });
    }
}
