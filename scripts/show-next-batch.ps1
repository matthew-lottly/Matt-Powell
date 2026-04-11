Write-Host "Next issue batch"

$trackerPath = "docs/issue-filing-tracker.md"
if (-not (Test-Path $trackerPath)) {
    Write-Error "Tracker file not found: $trackerPath"
    exit 1
}

$tableLines = Get-Content $trackerPath | Where-Object { $_ -match '^\| ' }
if ($tableLines.Count -lt 3) {
    Write-Error "Tracker table is missing or malformed."
    exit 1
}

$headerSegments = $tableLines[0].Split('|')
$headers = $headerSegments[1..($headerSegments.Count - 2)].ForEach({ $_.Trim() })
$dataLines = $tableLines | Select-Object -Skip 2

$rows = foreach ($line in $dataLines) {
    $segments = $line.Split('|')
    $values = $segments[1..($segments.Count - 2)].ForEach({ $_.Trim() })
    $row = [ordered]@{}
    for ($index = 0; $index -lt $headers.Count; $index++) {
        $value = if ($index -lt $values.Count) { $values[$index] } else { '' }
        $row[$headers[$index]] = $value
    }
    [PSCustomObject]$row
}

$readyRows = $rows | Where-Object { $_.Status -eq 'Ready' } | Sort-Object Queue
if (-not $readyRows) {
    Write-Host "No ready issues remain in the tracker."
    exit 0
}

$firstQueue = [int]$readyRows[0].Queue
$batchName = switch ($firstQueue) {
    { $_ -ge 1 -and $_ -le 7 } { 'Batch 1'; break }
    { $_ -ge 8 -and $_ -le 13 } { 'Batch 2'; break }
    default { 'Batch 3' }
}

$batchRows = switch ($batchName) {
    'Batch 1' { $readyRows | Where-Object { [int]$_.Queue -ge 1 -and [int]$_.Queue -le 7 } }
    'Batch 2' { $readyRows | Where-Object { [int]$_.Queue -ge 8 -and [int]$_.Queue -le 13 } }
    default { $readyRows | Where-Object { [int]$_.Queue -ge 14 -and [int]$_.Queue -le 20 } }
}

Write-Host ("Active batch: " + $batchName)
foreach ($row in $batchRows) {
    Write-Host (("[{0}] {1} :: {2}") -f $row.Queue, $row.Repository, $row.'Submission file')
}