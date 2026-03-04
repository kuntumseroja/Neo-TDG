using MediatR;
using MassTransit;
using CoreTax.Application.Commands;
using CoreTax.Domain.Entities;
using CoreTax.Domain.Enums;
using CoreTax.Contracts.Events;

namespace CoreTax.Application.Handlers;

public class FileTaxReturnHandler : IRequestHandler<FileTaxReturnCommand, FileTaxReturnResult>
{
    private readonly ITaxReturnRepository _repository;
    private readonly IPublishEndpoint _publishEndpoint;
    private readonly ILogger<FileTaxReturnHandler> _logger;

    public FileTaxReturnHandler(
        ITaxReturnRepository repository,
        IPublishEndpoint publishEndpoint,
        ILogger<FileTaxReturnHandler> logger)
    {
        _repository = repository;
        _publishEndpoint = publishEndpoint;
        _logger = logger;
    }

    public async Task<FileTaxReturnResult> Handle(
        FileTaxReturnCommand request,
        CancellationToken cancellationToken)
    {
        var taxableIncome = request.GrossIncome - request.Deductions;
        var totalTax = CalculateTax(taxableIncome, request.ReturnType);
        var taxDue = totalTax - request.TaxCredits;

        var taxReturn = new TaxReturn
        {
            SptId = Guid.NewGuid(),
            Npwp = request.Npwp,
            TaxPeriod = request.TaxPeriod,
            TaxYear = request.TaxYear,
            GrossIncome = request.GrossIncome,
            Deductions = request.Deductions,
            TaxableIncome = taxableIncome,
            TotalTax = totalTax,
            TaxCredits = request.TaxCredits,
            TaxDue = Math.Max(0, taxDue),
            Overpayment = Math.Max(0, -taxDue),
            Status = TaxStatus.Submitted,
            FilingDate = DateTime.UtcNow
        };

        await _repository.AddAsync(taxReturn);
        await _repository.SaveChangesAsync(cancellationToken);

        await _publishEndpoint.Publish<TaxReturnFiledEvent>(
            new TaxReturnFiledEvent(
                taxReturn.SptId, taxReturn.Npwp, taxReturn.TaxPeriod,
                taxReturn.TaxYear, request.ReturnType, taxReturn.TaxDue,
                DateTime.UtcNow
            ),
            cancellationToken
        );

        return new FileTaxReturnResult
        {
            SptId = taxReturn.SptId,
            TaxDue = taxReturn.TaxDue,
            Overpayment = taxReturn.Overpayment,
            FilingDate = taxReturn.FilingDate.Value
        };
    }

    private decimal CalculateTax(decimal taxableIncome, string returnType)
    {
        // Progressive Indonesian income tax rates (PPh 21)
        if (taxableIncome <= 60_000_000m) return taxableIncome * 0.05m;
        if (taxableIncome <= 250_000_000m) return 3_000_000m + (taxableIncome - 60_000_000m) * 0.15m;
        if (taxableIncome <= 500_000_000m) return 31_500_000m + (taxableIncome - 250_000_000m) * 0.25m;
        if (taxableIncome <= 5_000_000_000m) return 94_000_000m + (taxableIncome - 500_000_000m) * 0.30m;
        return 1_444_000_000m + (taxableIncome - 5_000_000_000m) * 0.35m;
    }
}
