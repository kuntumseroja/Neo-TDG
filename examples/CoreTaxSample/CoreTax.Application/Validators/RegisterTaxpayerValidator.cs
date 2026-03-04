using FluentValidation;
using CoreTax.Application.Commands;

namespace CoreTax.Application.Validators;

public class RegisterTaxpayerValidator : AbstractValidator<RegisterTaxpayerCommand>
{
    public RegisterTaxpayerValidator()
    {
        RuleFor(x => x.Npwp)
            .NotEmpty().WithMessage("NPWP is required")
            .Length(15).WithMessage("NPWP must be exactly 15 digits")
            .Matches(@"^\d{15}$").WithMessage("NPWP must contain only digits");

        RuleFor(x => x.Name)
            .NotEmpty().WithMessage("Taxpayer name is required")
            .MaximumLength(200).WithMessage("Name cannot exceed 200 characters");

        RuleFor(x => x.Address)
            .NotEmpty().WithMessage("Address is required")
            .MaximumLength(500).WithMessage("Address cannot exceed 500 characters");

        RuleFor(x => x.Email)
            .NotEmpty().WithMessage("Email is required")
            .EmailAddress().WithMessage("Invalid email format");

        RuleFor(x => x.PhoneNumber)
            .NotEmpty().WithMessage("Phone number is required")
            .Matches(@"^(\+62|0)\d{9,12}$").WithMessage("Invalid Indonesian phone number");

        RuleFor(x => x.TaxpayerType)
            .NotEmpty().WithMessage("Taxpayer type is required")
            .Must(t => new[] { "Individual", "Corporate", "Government", "ForeignEntity" }.Contains(t))
            .WithMessage("Invalid taxpayer type");

        RuleFor(x => x.KppCode)
            .NotEmpty().WithMessage("KPP code is required")
            .Length(3).WithMessage("KPP code must be 3 characters");
    }
}
