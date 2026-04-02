Write-Host "Next issue to file"

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

$headers = $tableLines[0].Split('|').ForEach({ $_.Trim() }) | Where-Object { $_ -ne '' }
$dataLines = $tableLines | Select-Object -Skip 2

$rows = foreach ($line in $dataLines) {
    $values = $line.Split('|').ForEach({ $_.Trim() }) | Where-Object { $_ -ne '' }
    $row = [ordered]@{}
    for ($index = 0; $index -lt $headers.Count; $index++) {
        $value = if ($index -lt $values.Count) { $values[$index] } else { '' }
        $row[$headers[$index]] = $value
    }
    [PSCustomObject]$row
}

$pending = $rows | Where-Object {
    ($_.PSObject.Properties.Name -contains 'Status' -and $_.Status -eq 'Ready') -or
    ($_.PSObject.Properties.Name -contains 'Filed' -and $_.Filed -eq 'No')
} | Sort-Object Queue

if (-not $pending) {
    Write-Host "All tracked issues are marked filed."
    exit 0
}

$next = $pending | Select-Object -First 1
$submissionFile = if ($next.PSObject.Properties.Name -contains 'Submission file' -and $next.'Submission file') {
    $next.'Submission file'
} else {
    $submissionFiles = Get-ChildItem -Path "docs/issue-submissions" -File -Filter "*.md" |
        Where-Object { $_.Name -ne "README.md" }
    $match = $submissionFiles |
        Where-Object { $_.BaseName -match '^[0-9]{2}-' -and $_.BaseName -like ("*" + $next.Repository + "*") } |
        Select-Object -First 1
    if ($match) { "docs/issue-submissions/" + $match.Name } else { $null }
}

if ($next.PSObject.Properties.Name -contains 'Queue') {
    Write-Host ("Queue: " + $next.Queue)
}
Write-Host ("Repository: " + $next.Repository)
if ($next.PSObject.Properties.Name -contains 'Issue title') {
    Write-Host ("Issue: " + $next.'Issue title')
} else {
    Write-Host ("Issue: " + $next.Title)
}
Write-Host ("Priority: " + $next.Priority)
if ($submissionFile) {
    Write-Host ("Submission file: " + $submissionFile)
}