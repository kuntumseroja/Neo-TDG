using MediatR;
using CoreTax.Application.DTOs;

namespace CoreTax.Application.Queries;

public class GetInvoicesByPeriodQuery : IRequest<List<InvoiceDto>>
{
    public string Npwp { get; set; } = string.Empty;
    public string TaxPeriod { get; set; } = string.Empty;
    public int TaxYear { get; set; }
}
