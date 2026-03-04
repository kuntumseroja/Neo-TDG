using System.Net.Http.Json;
using System.Text.Json;

namespace CoreTax.Infrastructure.ExternalServices;

public class TaxPaymentGatewayClient
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<TaxPaymentGatewayClient> _logger;

    public TaxPaymentGatewayClient(
        IHttpClientFactory httpClientFactory,
        ILogger<TaxPaymentGatewayClient> logger)
    {
        _httpClient = httpClientFactory.CreateClient("PaymentGateway");
        _logger = logger;
    }

    public async Task<PaymentGatewayResponse> ProcessPaymentAsync(PaymentGatewayRequest request)
    {
        _logger.LogInformation("Sending payment to gateway: BillingCode={BillingCode}, Amount={Amount}",
            request.BillingCode, request.Amount);

        var content = JsonContent.Create(request);
        var response = await _httpClient.PostAsync("/api/payment/process", content);

        response.EnsureSuccessStatusCode();

        var result = await response.Content.ReadFromJsonAsync<PaymentGatewayResponse>();
        _logger.LogInformation("Payment gateway response: TransactionId={TransactionId}, Status={Status}",
            result?.TransactionId, result?.Status);

        return result!;
    }

    public async Task<PaymentStatusResponse> CheckPaymentStatusAsync(string transactionId)
    {
        var response = await _httpClient.GetAsync($"/api/payment/status/{transactionId}");
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<PaymentStatusResponse>()
            ?? throw new InvalidOperationException("Empty response from payment gateway");
    }

    public async Task<BillingCodeResponse> GenerateBillingCodeAsync(BillingCodeRequest request)
    {
        var content = JsonContent.Create(request);
        var response = await _httpClient.PostAsync("/api/billing/generate", content);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<BillingCodeResponse>()
            ?? throw new InvalidOperationException("Failed to generate billing code");
    }
}

public record PaymentGatewayRequest(string BillingCode, decimal Amount, string BankCode, string PaymentMethod);
public record PaymentGatewayResponse(string TransactionId, string Status, DateTime ProcessedAt);
public record PaymentStatusResponse(string TransactionId, string Status, DateTime? CompletedAt);
public record BillingCodeRequest(string Npwp, string TaxType, string TaxPeriod, decimal Amount);
public record BillingCodeResponse(string BillingCode, DateTime ExpiryDate);
