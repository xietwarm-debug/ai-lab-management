param(
  [string]$BaseUrl = "http://127.0.0.1:5000",
  [string]$Username,
  [string]$Password,
  [string]$LabSeedFile = "generated/asset-seed/lab_seed_import.txt",
  [string]$EquipmentCsvFile = "generated/asset-seed/equipment_seed_import.csv",
  [switch]$SkipLabs
)

$ErrorActionPreference = "Stop"

function Resolve-FullPath {
  param([string]$PathValue)
  if ([System.IO.Path]::IsPathRooted($PathValue)) {
    return [System.IO.Path]::GetFullPath($PathValue)
  }
  return [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $PathValue))
}

function Ensure-FileExists {
  param(
    [string]$PathValue,
    [string]$Label
  )
  $fullPath = Resolve-FullPath $PathValue
  if (-not (Test-Path $fullPath -PathType Leaf)) {
    throw "$Label not found: $fullPath"
  }
  return $fullPath
}

function New-JsonContent {
  param([object]$Payload)
  return New-Object System.Net.Http.StringContent(
    ($Payload | ConvertTo-Json -Depth 10),
    [System.Text.Encoding]::UTF8,
    "application/json"
  )
}

function Invoke-JsonPost {
  param(
    [System.Net.Http.HttpClient]$Client,
    [string]$Url,
    [object]$Payload,
    [hashtable]$Headers = @{}
  )

  $request = New-Object System.Net.Http.HttpRequestMessage([System.Net.Http.HttpMethod]::Post, $Url)
  foreach ($key in $Headers.Keys) {
    $request.Headers.TryAddWithoutValidation($key, [string]$Headers[$key]) | Out-Null
  }
  $request.Content = New-JsonContent $Payload
  $response = $Client.SendAsync($request).GetAwaiter().GetResult()
  $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
  if (-not $response.IsSuccessStatusCode) {
    throw "Request failed [$($response.StatusCode)] $Url`n$body"
  }
  return ($body | ConvertFrom-Json)
}

function Invoke-MultipartUpload {
  param(
    [System.Net.Http.HttpClient]$Client,
    [string]$Url,
    [string]$Token,
    [string]$FilePath
  )

  $fileName = [System.IO.Path]::GetFileName($FilePath)
  $bytes = [System.IO.File]::ReadAllBytes($FilePath)
  $fileContent = New-Object System.Net.Http.ByteArrayContent($bytes)
  $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("text/csv")

  $multipart = New-Object System.Net.Http.MultipartFormDataContent
  $multipart.Add($fileContent, "file", $fileName)

  $request = New-Object System.Net.Http.HttpRequestMessage([System.Net.Http.HttpMethod]::Post, $Url)
  $request.Headers.TryAddWithoutValidation("Authorization", "Bearer $Token") | Out-Null
  $request.Content = $multipart

  $response = $Client.SendAsync($request).GetAwaiter().GetResult()
  $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
  if (-not $response.IsSuccessStatusCode) {
    throw "Upload failed [$($response.StatusCode)] $Url`n$body"
  }
  return ($body | ConvertFrom-Json)
}

function Parse-LabSeedFile {
  param([string]$FilePath)

  $rows = @()
  $index = 0
  Get-Content -Path $FilePath -Encoding UTF8 | ForEach-Object {
    $line = [string]$_
    if ([string]::IsNullOrWhiteSpace($line)) {
      return
    }
    $parts = $line.Split(",")
    while ($parts.Count -lt 6) {
      $parts += ""
    }
    $index += 1
    $rows += [PSCustomObject]@{
      LineNo = $index
      Name = $parts[0].Trim()
      Location = $parts[1].Trim()
      Capacity = $parts[2].Trim()
      Manager = $parts[3].Trim()
      OpenHours = $parts[4].Trim()
      CoverUrl = $parts[5].Trim()
    }
  }
  return $rows
}

function Build-LabPayload {
  param($LabRow)

  $descriptionParts = @()
  if ($LabRow.Location) { $descriptionParts += $LabRow.Location }
  if ($LabRow.Manager) { $descriptionParts += "manager:$($LabRow.Manager)" }
  if ($LabRow.OpenHours) { $descriptionParts += "open_hours:$($LabRow.OpenHours)" }

  $capacity = 0
  [void][int]::TryParse([string]$LabRow.Capacity, [ref]$capacity)

  return @{
    name = $LabRow.Name
    status = "free"
    capacity = $capacity
    deviceCount = 0
    description = ($descriptionParts -join "; ")
    imageUrl = $LabRow.CoverUrl
  }
}

function Ensure-Labs {
  param(
    [System.Net.Http.HttpClient]$Client,
    [string]$BaseApiUrl,
    [string]$Token,
    [string]$LabFilePath
  )

  $rows = Parse-LabSeedFile $LabFilePath
  if (-not $rows.Count) {
    Write-Host "No lab seed rows found. Skip lab creation."
    return
  }

  $created = 0
  $skipped = 0
  foreach ($row in $rows) {
    $payload = Build-LabPayload $row
    try {
      $result = Invoke-JsonPost -Client $Client -Url "$BaseApiUrl/labs" -Payload $payload -Headers @{ Authorization = "Bearer $Token" }
      if ($result.ok -eq $true) {
        $created += 1
        Write-Host "Lab created: $($row.Name)"
      } else {
        throw ($result | ConvertTo-Json -Depth 5)
      }
    } catch {
      $message = $_.Exception.Message
      if ($message -match "409" -or $message -match "lab name exists") {
        $skipped += 1
        Write-Host "Lab exists, skipped: $($row.Name)"
      } else {
        throw "Lab create failed [$($row.Name)] $message"
      }
    }
  }

  Write-Host "Labs done. Created: $created; Skipped: $skipped"
}

if (-not $Username) {
  $Username = Read-Host "Admin username"
}

if (-not $Password) {
  $securePassword = Read-Host "Admin password" -AsSecureString
  $Password = [System.Net.NetworkCredential]::new("", $securePassword).Password
}

$equipmentCsvFullPath = Ensure-FileExists -PathValue $EquipmentCsvFile -Label "Equipment CSV"
$labSeedFullPath = $null
if (-not $SkipLabs) {
  $labSeedFullPath = Ensure-FileExists -PathValue $LabSeedFile -Label "Lab seed file"
}

$normalizedBaseUrl = $BaseUrl.TrimEnd("/")
$loginUrl = "$normalizedBaseUrl/login"
$importUrl = "$normalizedBaseUrl/equipments/import"

$clientHandler = New-Object System.Net.Http.HttpClientHandler
$client = New-Object System.Net.Http.HttpClient($clientHandler)
$client.Timeout = [TimeSpan]::FromMinutes(10)

try {
  Write-Host "Logging in: $normalizedBaseUrl"
  $loginResult = Invoke-JsonPost -Client $client -Url $loginUrl -Payload @{
    username = $Username
    password = $Password
    deviceName = "asset-seed-import-script"
  }

  if ($loginResult.ok -ne $true -or -not $loginResult.data.token) {
    throw "Login failed: $($loginResult | ConvertTo-Json -Depth 5)"
  }

  $token = [string]$loginResult.data.token
  $role = [string]$loginResult.data.role
  Write-Host "Login ok. Role: $role"

  if (-not $SkipLabs) {
    Ensure-Labs -Client $client -BaseApiUrl $normalizedBaseUrl -Token $token -LabFilePath $labSeedFullPath
  }

  Write-Host "Uploading equipment CSV: $equipmentCsvFullPath"
  $importResult = Invoke-MultipartUpload -Client $client -Url $importUrl -Token $token -FilePath $equipmentCsvFullPath
  if ($importResult.ok -ne $true) {
    throw "Equipment import failed: $($importResult | ConvertTo-Json -Depth 10)"
  }

  $data = $importResult.data
  Write-Host "Equipment import done."
  Write-Host ("Inserted: {0}; Updated: {1}; Failed: {2}" -f $data.inserted, $data.updated, $data.failed)

  if ($data.failed -gt 0 -and $data.errors) {
    Write-Host "Top errors:"
    $data.errors | Select-Object -First 20 | ForEach-Object {
      Write-Host ("  Row {0}: {1}" -f $_.row, $_.reason)
    }
  }
} finally {
  $client.Dispose()
}
