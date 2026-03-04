using Amazon.S3;
using Amazon.S3.Model;

namespace CoreTax.Infrastructure.ExternalServices;

public class DocumentStorageService
{
    private readonly IAmazonS3 _s3Client;
    private readonly ILogger<DocumentStorageService> _logger;
    private readonly string _bucketName;

    public DocumentStorageService(
        IAmazonS3 s3Client,
        IConfiguration configuration,
        ILogger<DocumentStorageService> logger)
    {
        _s3Client = s3Client;
        _logger = logger;
        _bucketName = configuration["S3:BucketName"] ?? "coretax-documents";
    }

    public async Task<string> UploadInvoiceDocumentAsync(Guid invoiceId, Stream fileStream, string fileName)
    {
        var key = $"invoices/{invoiceId}/{fileName}";
        _logger.LogInformation("Uploading document to S3: {Key}", key);

        var request = new PutObjectRequest
        {
            BucketName = _bucketName,
            Key = key,
            InputStream = fileStream,
            ContentType = GetContentType(fileName),
            ServerSideEncryptionMethod = ServerSideEncryptionMethod.AES256
        };

        await _s3Client.PutObjectAsync(request);
        _logger.LogInformation("Document uploaded successfully: {Key}", key);
        return key;
    }

    public async Task<Stream> DownloadDocumentAsync(string key)
    {
        var request = new GetObjectRequest
        {
            BucketName = _bucketName,
            Key = key
        };

        var response = await _s3Client.GetObjectAsync(request);
        return response.ResponseStream;
    }

    public async Task<List<string>> ListTaxpayerDocumentsAsync(string npwp)
    {
        var request = new ListObjectsV2Request
        {
            BucketName = _bucketName,
            Prefix = $"taxpayers/{npwp}/"
        };

        var response = await _s3Client.ListObjectsV2Async(request);
        return response.S3Objects.Select(o => o.Key).ToList();
    }

    public async Task DeleteDocumentAsync(string key)
    {
        await _s3Client.DeleteObjectAsync(_bucketName, key);
        _logger.LogInformation("Document deleted: {Key}", key);
    }

    private string GetContentType(string fileName)
    {
        return Path.GetExtension(fileName).ToLower() switch
        {
            ".pdf" => "application/pdf",
            ".xml" => "application/xml",
            ".json" => "application/json",
            ".csv" => "text/csv",
            _ => "application/octet-stream"
        };
    }
}
