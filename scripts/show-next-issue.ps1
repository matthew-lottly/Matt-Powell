Write-Host "Next issue to file"

$trackerPath = "docs/issue-filing-tracker.md"
if (-not (Test-Path $trackerPath)) {
    Write-Error "Tracker file not found: $trackerPath"
    exit 1
}

$rows = Get-Content $trackerPath | Where-Object { $_ -match '^\| ' -and $_ -notmatch '^\| ---' }
$pending = $rows | ForEach-Object {
    $parts = $_.Split('|').ForEach({ $_.Trim() })
    [PSCustomObject]@{
        Repository = $parts[1]
        Title = $parts[2]
        Priority = $parts[3]
        Filed = $parts[4]
        Link = $parts[5]
    }
} | Where-Object { $_.Filed -eq 'No' }

if (-not $pending) {
    Write-Host "All tracked issues are marked filed."
    exit 0
}

$next = $pending | Select-Object -First 1
Write-Host ("Repository: " + $next.Repository)
Write-Host ("Issue: " + $next.Title)
Write-Host ("Priority: " + $next.Priority)