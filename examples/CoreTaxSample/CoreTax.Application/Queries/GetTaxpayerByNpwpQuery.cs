using MediatR;
using CoreTax.Application.DTOs;

namespace CoreTax.Application.Queries;

public class GetTaxpayerByNpwpQuery : IRequest<TaxpayerDto>
{
    public string Npwp { get; set; } = string.Empty;
}
