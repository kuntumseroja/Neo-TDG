using Microsoft.EntityFrameworkCore;
using CoreTax.Domain.Entities;

namespace CoreTax.Infrastructure.Persistence.Repositories;

public interface ITaxpayerRepository
{
    Task<Taxpayer?> GetByNpwpAsync(string npwp);
    Task<Taxpayer?> GetByIdAsync(Guid id);
    Task<List<Taxpayer>> GetAllActiveAsync();
    Task AddAsync(Taxpayer taxpayer);
    Task SaveChangesAsync(CancellationToken cancellationToken = default);
}

public class TaxpayerRepository : ITaxpayerRepository
{
    private readonly CoreTaxDbContext _context;

    public TaxpayerRepository(CoreTaxDbContext context)
    {
        _context = context;
    }

    public async Task<Taxpayer?> GetByNpwpAsync(string npwp)
    {
        return await _context.Taxpayers
            .FirstOrDefaultAsync(t => t.Npwp == npwp);
    }

    public async Task<Taxpayer?> GetByIdAsync(Guid id)
    {
        return await _context.Taxpayers.FindAsync(id);
    }

    public async Task<List<Taxpayer>> GetAllActiveAsync()
    {
        return await _context.Taxpayers
            .Where(t => t.IsActive)
            .OrderBy(t => t.Name)
            .ToListAsync();
    }

    public async Task AddAsync(Taxpayer taxpayer)
    {
        await _context.Taxpayers.AddAsync(taxpayer);
    }

    public async Task SaveChangesAsync(CancellationToken cancellationToken = default)
    {
        await _context.SaveChangesAsync(cancellationToken);
    }
}
