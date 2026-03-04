using Microsoft.AspNetCore.Authorization;

namespace CoreTax.Shared.Auth;

public class TaxOfficerRequirement : IAuthorizationRequirement
{
    public string MinimumRole { get; }

    public TaxOfficerRequirement(string minimumRole)
    {
        MinimumRole = minimumRole;
    }
}

public class CoreTaxAuthorizationHandler : AuthorizationHandler<TaxOfficerRequirement>
{
    protected override Task HandleRequirementAsync(
        AuthorizationHandlerContext context,
        TaxOfficerRequirement requirement)
    {
        var roleClaim = context.User.FindFirst(System.Security.Claims.ClaimTypes.Role);
        if (roleClaim == null)
        {
            context.Fail();
            return Task.CompletedTask;
        }

        var roleHierarchy = new[] { "Viewer", "Officer", "Supervisor", "Admin" };
        var userRoleIndex = Array.IndexOf(roleHierarchy, roleClaim.Value);
        var requiredRoleIndex = Array.IndexOf(roleHierarchy, requirement.MinimumRole);

        if (userRoleIndex >= requiredRoleIndex)
        {
            context.Succeed(requirement);
        }
        else
        {
            context.Fail();
        }

        return Task.CompletedTask;
    }
}
