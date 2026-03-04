using MediatR;
using CoreTax.Application.DTOs;

namespace CoreTax.Application.Queries;

public class GetTaxReturnStatusQuery : IRequest<TaxReturnDto>
{
    public Guid SptId { get; set; }
    public string Npwp { get; set; } = string.Empty;
}
