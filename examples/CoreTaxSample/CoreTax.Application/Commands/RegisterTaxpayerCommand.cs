using MediatR;

namespace CoreTax.Application.Commands;

public class RegisterTaxpayerCommand : IRequest<RegisterTaxpayerResult>
{
    public string Npwp { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string Address { get; set; } = string.Empty;
    public string Email { get; set; } = string.Empty;
    public string PhoneNumber { get; set; } = string.Empty;
    public string TaxpayerType { get; set; } = string.Empty;
    public string KppCode { get; set; } = string.Empty;
}

public class RegisterTaxpayerResult
{
    public Guid TaxpayerId { get; set; }
    public string Npwp { get; set; } = string.Empty;
    public DateTime RegistrationDate { get; set; }
}
