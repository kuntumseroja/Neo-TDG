using FluentValidation;
using CoreTax.Application.Commands;

namespace CoreTax.Application.Validators;

public class SubmitInvoiceValidator : AbstractValidator<SubmitInvoiceCommand>
{
    public SubmitInvoiceValidator()
    {
        RuleFor(x => x.InvoiceNumber)
            .NotEmpty().WithMessage("Invoice number is required")
            .Matches(@"^\d{3}-\d{3}\.\d{2}-\d{8}$").WithMessage("Invalid invoice number format (XXX-XXX.XX-XXXXXXXX)");

        RuleFor(x => x.SellerNpwp)
            .NotEmpty().WithMessage("Seller NPWP is required")
            .Length(15).WithMessage("Seller NPWP must be 15 digits");

        RuleFor(x => x.BuyerNpwp)
            .NotEmpty().WithMessage("Buyer NPWP is required")
            .Length(15).WithMessage("Buyer NPWP must be 15 digits");

        RuleFor(x => x.TaxableAmount)
            .GreaterThan(0).WithMessage("Taxable amount must be positive");

        RuleFor(x => x.VatAmount)
            .GreaterThanOrEqualTo(0).WithMessage("VAT amount cannot be negative");

        RuleFor(x => x.InvoiceDate)
            .NotEmpty().WithMessage("Invoice date is required")
            .LessThanOrEqualTo(DateTime.UtcNow.AddDays(1)).WithMessage("Invoice date cannot be in the future");

        RuleFor(x => x.Items)
            .NotEmpty().WithMessage("Invoice must have at least one item");

        RuleForEach(x => x.Items).ChildRules(item =>
        {
            item.RuleFor(i => i.ItemName).NotEmpty().WithMessage("Item name is required");
            item.RuleFor(i => i.Quantity).GreaterThan(0).WithMessage("Quantity must be positive");
            item.RuleFor(i => i.UnitPrice).GreaterThan(0).WithMessage("Unit price must be positive");
        });
    }
}
