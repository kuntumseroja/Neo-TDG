FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

COPY ["CoreTax.Worker/CoreTax.Worker.csproj", "CoreTax.Worker/"]
COPY ["CoreTax.Application/CoreTax.Application.csproj", "CoreTax.Application/"]
COPY ["CoreTax.Infrastructure/CoreTax.Infrastructure.csproj", "CoreTax.Infrastructure/"]
COPY ["CoreTax.Domain/CoreTax.Domain.csproj", "CoreTax.Domain/"]
COPY ["CoreTax.Contracts/CoreTax.Contracts.csproj", "CoreTax.Contracts/"]
COPY ["CoreTax.Shared/CoreTax.Shared.csproj", "CoreTax.Shared/"]

RUN dotnet restore "CoreTax.Worker/CoreTax.Worker.csproj"
COPY . .
RUN dotnet build "CoreTax.Worker/CoreTax.Worker.csproj" -c Release -o /app/build
RUN dotnet publish "CoreTax.Worker/CoreTax.Worker.csproj" -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime
WORKDIR /app
COPY --from=build /app/publish .

ENV ASPNETCORE_ENVIRONMENT=Production
ENV RabbitMQ__Host=rabbitmq
ENV ConnectionStrings__HangfireConnection="Server=sqlserver;Database=CoreTax_Hangfire;User=sa;Password=CoreTax@2024;"

ENTRYPOINT ["dotnet", "CoreTax.Worker.dll"]
