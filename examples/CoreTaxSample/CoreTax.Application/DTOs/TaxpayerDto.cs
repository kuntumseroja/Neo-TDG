namespace CoreTax.Application.DTOs;

public class TaxpayerDto
{
    public Guid TaxpayerId { get; set; }
    public string Npwp { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string Address { get; set; } = string.Empty;
    public string Email { get; set; } = string.Empty;
    public string TaxpayerType { get; set; } = string.Empty;
    public string RegistrationStatus { get; set; } = string.Empty;
    public DateTime RegistrationDate { get; set; }
    public bool IsActive { get; set; }
}
