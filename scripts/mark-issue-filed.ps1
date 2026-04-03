param(
    [Parameter(Mandatory = $true)]
    [string]$Queue,

    [Parameter(Mandatory = $true)]
    [string]$IssueReference,

    [string]$Owner = "",

    [string]$FiledOn = "",

    [string]$Notes = ""
)

$trackerPath = "docs/issue-filing-tracker.md"
if (-not (Test-Path $trackerPath)) {
    Write-Error "Tracker file not found: $trackerPath"
    exit 1
}

$resolvedDate = if ($FiledOn) { $FiledOn } else { Get-Date -Format 'yyyy-MM-dd' }
$lines = Get-Content $trackerPath
$updated = $false

for ($index = 0; $index -lt $lines.Count; $index++) {
    $line = $lines[$index]
    if ($line -notmatch '^\| ') {
        continue
    }

    $values = $line.Split('|').ForEach({ $_.Trim() })
    if ($values.Count -lt 11) {
        continue
    }

    if ($values[1] -ne $Queue) {
        continue
    }

    $notesValue = if ($Notes) { $Notes } else { $values[10] }
    $ownerValue = if ($Owner) { $Owner } else { $values[6] }
    $newLine = "| {0} | {1} | {2} | {3} | Filed | {4} | {5} | {6} | {7} | {8} |" -f \
        $values[1], $values[2], $values[3], $values[4], $ownerValue, $resolvedDate, $IssueReference, $values[9], $notesValue
    $lines[$index] = $newLine
    $updated = $true
    break
}

if (-not $updated) {
    Write-Error ("Queue item not found in tracker: " + $Queue)
    exit 1
}

Set-Content -Path $trackerPath -Value $lines
Write-Host ("Updated tracker item " + $Queue + " as Filed")