param(
    [Parameter(Mandatory = $true)]
    [string]$DestinationRoot
)

$plans = @(
    @{ Name = "environmental-monitoring-api"; Source = "D:\GitHub\projects\spatial-data-api"; Exclude = @(".pytest_cache", "__pycache__", ".venv") },
    @{ Name = "environmental-monitoring-analytics"; Source = "D:\GitHub\projects\environmental-monitoring-analytics"; Exclude = @(".pytest_cache", "__pycache__", ".venv") },
    @{ Name = "monitoring-data-warehouse"; Source = "D:\GitHub\projects\monitoring-data-warehouse"; Exclude = @(".pytest_cache", "__pycache__", ".venv", "monitoring_warehouse.duckdb") },
    @{ Name = "experience-builder-station-brief-widget"; Source = "D:\GitHub\projects\experience-builder-station-brief-widget"; Exclude = @("node_modules", "dist") }
)

New-Item -ItemType Directory -Path $DestinationRoot -Force | Out-Null

foreach ($plan in $plans) {
    $target = Join-Path $DestinationRoot $plan.Name
    New-Item -ItemType Directory -Path $target -Force | Out-Null
    Get-ChildItem -Path $plan.Source -Force | Where-Object { $plan.Exclude -notcontains $_.Name } | ForEach-Object {
        Copy-Item -Path $_.FullName -Destination $target -Recurse -Force
    }
    Write-Host "Prepared $($plan.Name) at $target"
}

Write-Host "All project folders copied. Next: initialize git in each extracted folder and push to separate repositories."