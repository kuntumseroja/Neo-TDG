namespace CoreTax.Domain.ValueObjects;

public record Npwp
{
    public string Value { get; }

    public Npwp(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
            throw new ArgumentException("NPWP cannot be empty");

        var cleaned = value.Replace(".", "").Replace("-", "");
        if (cleaned.Length != 15 || !cleaned.All(char.IsDigit))
            throw new ArgumentException("NPWP must be 15 digits (XX.XXX.XXX.X-XXX.XXX)");

        Value = cleaned;
    }

    public string Formatted =>
        $"{Value[..2]}.{Value[2..5]}.{Value[5..8]}.{Value[8]}-{Value[9..12]}.{Value[12..15]}";

    public override string ToString() => Formatted;
}
