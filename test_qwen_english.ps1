# Test Qwen request with English
$url = "http://localhost:7777/v1/chat/completions"

$body = @{
    provider = "qwen"
    model = "qwen-max"
    messages = @(
        @{
            role = "user"
            content = "Hello! Please respond with just 'Hi there!' to confirm you're working."
        }
    )
} | ConvertTo-Json -Depth 10

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "Prompt Bridge - Qwen Test (English)" -ForegroundColor Yellow
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

Write-Host "Request URL: " -NoNewline -ForegroundColor Green
Write-Host $url
Write-Host ""
Write-Host "Request Body:" -ForegroundColor Green
Write-Host $body
Write-Host ""
Write-Host "Sending request..." -ForegroundColor Yellow
Write-Host "(This may take 30-60 seconds as the browser navigates to Qwen AI)" -ForegroundColor Gray
Write-Host ""

try {
    $response = Invoke-WebRequest -Uri $url -Method POST -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 120
    
    Write-Host "Status: " -NoNewline -ForegroundColor Green
    Write-Host $response.StatusCode
    Write-Host ""
    
    $result = $response.Content | ConvertFrom-Json
    Write-Host "Response:" -ForegroundColor Green
    Write-Host ($result | ConvertTo-Json -Depth 10)
    Write-Host ""
    
    if ($result.choices -and $result.choices.Count -gt 0) {
        $message = $result.choices[0].message.content
        Write-Host "✅ Qwen Response: " -NoNewline -ForegroundColor Green
        Write-Host $message -ForegroundColor White
    }
    
    Write-Host ""
    Write-Host "✅ Test completed successfully!" -ForegroundColor Green
} catch {
    Write-Host "❌ Error: " -NoNewline -ForegroundColor Red
    Write-Host $_.Exception.Message
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response Body: $responseBody" -ForegroundColor Red
    }
}
