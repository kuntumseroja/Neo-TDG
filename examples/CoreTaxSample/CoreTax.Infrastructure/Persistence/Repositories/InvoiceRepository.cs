using Microsoft.EntityFrameworkCore;
using CoreTax.Domain.Entities;

namespace CoreTax.Infrastructure.Persistence.Repositories;

public interface IInvoiceRepository
{
    Task<TaxInvoice?> GetByIdAsync(Guid id);
    Task<TaxInvoice?> GetByNumberAsync(string invoiceNumber);
    Task<List<TaxInvoice>> GetBySellerAsync(string sellerNpwp, string period);
    Task<List<TaxInvoice>> GetByBuyerAsync(string buyerNpwp, string period);
    Task AddAsync(TaxInvoice invoice);
    void Update(TaxInvoice invoice);
    Task SaveChangesAsync(CancellationToken cancellationToken = default);
}

public class InvoiceRepository : IInvoiceRepository
{
    private readonly CoreTaxDbContext _context;

    public InvoiceRepository(CoreTaxDbContext context)
    {
        _context = context;
    }

    public async Task<TaxInvoice?> GetByIdAsync(Guid id)
    {
        return await _context.TaxInvoices
            .Include(i => i.Items)
            .FirstOrDefaultAsync(i => i.InvoiceId == id);
    }

    public async Task<TaxInvoice?> GetByNumberAsync(string invoiceNumber)
    {
        return await _context.TaxInvoices
            .Include(i => i.Items)
            .FirstOrDefaultAsync(i => i.InvoiceNumber == invoiceNumber);
    }

    public async Task<List<TaxInvoice>> GetBySellerAsync(string sellerNpwp, string period)
    {
        return await _context.TaxInvoices
            .Where(i => i.SellerNpwp == sellerNpwp)
            .OrderByDescending(i => i.InvoiceDate)
            .ToListAsync();
    }

    public async Task<List<TaxInvoice>> GetByBuyerAsync(string buyerNpwp, string period)
    {
        return await _context.TaxInvoices
            .Where(i => i.BuyerNpwp == buyerNpwp)
            .OrderByDescending(i => i.InvoiceDate)
            .ToListAsync();
    }

    public async Task AddAsync(TaxInvoice invoice)
    {
        await _context.TaxInvoices.AddAsync(invoice);
    }

    public void Update(TaxInvoice invoice)
    {
        _context.TaxInvoices.Update(invoice);
    }

    public async Task SaveChangesAsync(CancellationToken cancellationToken = default)
    {
        await _context.SaveChangesAsync(cancellationToken);
    }
}
