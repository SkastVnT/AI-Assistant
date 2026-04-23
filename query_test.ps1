$apiKey = "sk-76aTnsuUt2Gw_-LneRMQbdCbVwoyNX5nKMNGlZCRe7hZVmu0"
$headers = @{ "Authorization" = "Bearer $apiKey"; "Content-Type" = "application/json"; "apollo-require-preflight" = "true" }
$body = @{ query = "{ __schema { queryType { fields { name } } } }" } | ConvertTo-Json
try {
  $r = Invoke-RestMethod -Uri "https://api.pixai.art/graphql" -Method POST -Headers $headers -Body $body
  $r | ConvertTo-Json -Depth 5
} catch {
  $_.Exception.Message
  if ($_.Exception.Response) {
    $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
    $reader.ReadToEnd()
  }
}
