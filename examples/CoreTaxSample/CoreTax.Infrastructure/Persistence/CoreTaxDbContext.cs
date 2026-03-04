using Microsoft.EntityFrameworkCore;
using CoreTax.Domain.Entities;

namespace CoreTax.Infrastructure.Persistence;

public class CoreTaxDbContext : DbContext
{
    public CoreTaxDbContext(DbContextOptions<CoreTaxDbContext> options) : base(options) { }

    public DbSet<Taxpayer> Taxpayers { get; set; }
    public DbSet<TaxInvoice> TaxInvoices { get; set; }
    public DbSet<TaxReturn> TaxReturns { get; set; }
    public DbSet<TaxPayment> TaxPayments { get; set; }
    public DbSet<TaxAudit> TaxAudits { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Taxpayer>(entity =>
        {
            entity.ToTable("taxpayers");
            entity.HasKey(e => e.TaxpayerId);
            entity.HasIndex(e => e.Npwp).IsUnique();
            entity.Property(e => e.Npwp).HasMaxLength(15).IsRequired();
            entity.Property(e => e.Name).HasMaxLength(200).IsRequired();
            entity.Property(e => e.Address).HasMaxLength(500);
            entity.Property(e => e.Email).HasMaxLength(100);
        });

        modelBuilder.Entity<TaxInvoice>(entity =>
        {
            entity.ToTable("tax_invoices");
            entity.HasKey(e => e.InvoiceId);
            entity.HasIndex(e => e.InvoiceNumber).IsUnique();
            entity.Property(e => e.TaxableAmount).HasColumnType("decimal(18,2)");
            entity.Property(e => e.VatAmount).HasColumnType("decimal(18,2)");
        });

        modelBuilder.Entity<TaxReturn>(entity =>
        {
            entity.ToTable("tax_returns");
            entity.HasKey(e => e.SptId);
            entity.Property(e => e.GrossIncome).HasColumnType("decimal(18,2)");
            entity.Property(e => e.TotalTax).HasColumnType("decimal(18,2)");
            entity.Property(e => e.TaxDue).HasColumnType("decimal(18,2)");
        });

        modelBuilder.Entity<TaxPayment>(entity =>
        {
            entity.ToTable("tax_payments");
            entity.HasKey(e => e.PaymentId);
            entity.HasIndex(e => e.BillingCode).IsUnique();
            entity.Property(e => e.Amount).HasColumnType("decimal(18,2)");
            entity.Property(e => e.TotalAmount).HasColumnType("decimal(18,2)");
        });

        modelBuilder.Entity<TaxAudit>(entity =>
        {
            entity.ToTable("tax_audits");
            entity.HasKey(e => e.AuditId);
            entity.Property(e => e.FindingsAmount).HasColumnType("decimal(18,2)");
            entity.Property(e => e.PenaltyAmount).HasColumnType("decimal(18,2)");
        });
    }
}
