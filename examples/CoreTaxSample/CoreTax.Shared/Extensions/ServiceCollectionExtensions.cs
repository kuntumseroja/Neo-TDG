using Microsoft.Extensions.DependencyInjection;
using CoreTax.Shared.Auth;

namespace CoreTax.Shared.Extensions;

public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddCoreTaxAuthentication(this IServiceCollection services, IConfiguration configuration)
    {
        services.AddSingleton<JwtTokenService>();
        services.AddAuthentication("Bearer")
            .AddJwtBearer(options =>
            {
                options.TokenValidationParameters = new Microsoft.IdentityModel.Tokens.TokenValidationParameters
                {
                    ValidateIssuer = true,
                    ValidateAudience = true,
                    ValidateLifetime = true,
                    ValidIssuer = configuration["Jwt:Issuer"] ?? "CoreTax",
                    ValidAudience = configuration["Jwt:Audience"] ?? "CoreTaxAPI"
                };
            });

        services.AddAuthorization(options =>
        {
            options.AddPolicy("TaxOfficer", policy =>
                policy.Requirements.Add(new TaxOfficerRequirement("Officer")));
            options.AddPolicy("Supervisor", policy =>
                policy.Requirements.Add(new TaxOfficerRequirement("Supervisor")));
            options.AddPolicy("Admin", policy =>
                policy.Requirements.Add(new TaxOfficerRequirement("Admin")));
        });

        return services;
    }
}
