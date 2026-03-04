using Microsoft.Extensions.Caching.Distributed;
using StackExchange.Redis;
using System.Text.Json;

namespace CoreTax.Infrastructure.Caching;

public class RedisCacheService
{
    private readonly IConnectionMultiplexer _redis;
    private readonly IDistributedCache _cache;
    private readonly IDatabase _database;
    private readonly ILogger<RedisCacheService> _logger;

    public RedisCacheService(
        IConnectionMultiplexer redis,
        IDistributedCache cache,
        ILogger<RedisCacheService> logger)
    {
        _redis = redis;
        _cache = cache;
        _database = redis.GetDatabase();
        _logger = logger;
    }

    public async Task<T?> GetAsync<T>(string key)
    {
        var cached = await _cache.GetStringAsync(key);
        if (cached == null) return default;

        _logger.LogDebug("Cache hit for key: {Key}", key);
        return JsonSerializer.Deserialize<T>(cached);
    }

    public async Task SetAsync<T>(string key, T value, TimeSpan? expiry = null)
    {
        var options = new DistributedCacheEntryOptions
        {
            AbsoluteExpirationRelativeToNow = expiry ?? TimeSpan.FromMinutes(30)
        };

        var serialized = JsonSerializer.Serialize(value);
        await _cache.SetStringAsync(key, serialized, options);
        _logger.LogDebug("Cache set for key: {Key}", key);
    }

    public async Task RemoveAsync(string key)
    {
        await _cache.RemoveAsync(key);
        _logger.LogDebug("Cache removed for key: {Key}", key);
    }

    public async Task<long> IncrementAsync(string key)
    {
        return await _database.StringIncrementAsync(key);
    }

    public async Task InvalidateTaxpayerCacheAsync(string npwp)
    {
        var server = _redis.GetServer(_redis.GetEndPoints().First());
        var keys = server.Keys(pattern: $"taxpayer:{npwp}:*");
        foreach (var key in keys)
        {
            await _database.KeyDeleteAsync(key);
        }
        _logger.LogInformation("Cache invalidated for taxpayer: {Npwp}", npwp);
    }
}
