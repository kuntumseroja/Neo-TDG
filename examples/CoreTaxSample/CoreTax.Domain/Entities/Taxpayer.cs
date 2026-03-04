using CoreTax.Domain.ValueObjects;
using CoreTax.Domain.Enums;

namespace CoreTax.Domain.Entities;

public class Taxpayer
{
    public Guid TaxpayerId { get; set; }
    public string Npwp { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string Address { get; set; } = string.Empty;
    public string Email { get; set; } = string.Empty;
    public string PhoneNumber { get; set; } = string.Empty;
    public TaxpayerType TaxpayerType { get; set; }
    public TaxStatus RegistrationStatus { get; set; }
    public DateTime RegistrationDate { get; set; }
    public DateTime? ActivationDate { get; set; }
    public string KppCode { get; set; } = string.Empty;
    public bool IsActive { get; set; }
}

public enum TaxpayerType
{
    Individual,
    Corporate,
    Government,
    ForeignEntity
}
