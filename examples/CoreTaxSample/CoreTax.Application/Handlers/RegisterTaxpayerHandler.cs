using MediatR;
using MassTransit;
using CoreTax.Application.Commands;
using CoreTax.Domain.Entities;
using CoreTax.Contracts.Events;

namespace CoreTax.Application.Handlers;

public class RegisterTaxpayerHandler : IRequestHandler<RegisterTaxpayerCommand, RegisterTaxpayerResult>
{
    private readonly ITaxpayerRepository _repository;
    private readonly IPublishEndpoint _publishEndpoint;
    private readonly ILogger<RegisterTaxpayerHandler> _logger;

    public RegisterTaxpayerHandler(
        ITaxpayerRepository repository,
        IPublishEndpoint publishEndpoint,
        ILogger<RegisterTaxpayerHandler> logger)
    {
        _repository = repository;
        _publishEndpoint = publishEndpoint;
        _logger = logger;
    }

    public async Task<RegisterTaxpayerResult> Handle(
        RegisterTaxpayerCommand request,
        CancellationToken cancellationToken)
    {
        _logger.LogInformation("Registering taxpayer with NPWP: {Npwp}", request.Npwp);

        var taxpayer = new Taxpayer
        {
            TaxpayerId = Guid.NewGuid(),
            Npwp = request.Npwp,
            Name = request.Name,
            Address = request.Address,
            Email = request.Email,
            PhoneNumber = request.PhoneNumber,
            RegistrationDate = DateTime.UtcNow,
            IsActive = true
        };

        await _repository.AddAsync(taxpayer);
        await _repository.SaveChangesAsync(cancellationToken);

        await _publishEndpoint.Publish<TaxpayerRegisteredEvent>(
            new TaxpayerRegisteredEvent(
                taxpayer.TaxpayerId,
                taxpayer.Npwp,
                taxpayer.Name,
                request.TaxpayerType,
                DateTime.UtcNow
            ),
            cancellationToken
        );

        _logger.LogInformation("Taxpayer registered successfully: {TaxpayerId}", taxpayer.TaxpayerId);

        return new RegisterTaxpayerResult
        {
            TaxpayerId = taxpayer.TaxpayerId,
            Npwp = taxpayer.Npwp,
            RegistrationDate = taxpayer.RegistrationDate
        };
    }
}
