param(
    [Parameter(Mandatory = $true)]
    [string]$DestinationPath
)

$source = "D:\GitHub\projects\experience-builder-station-brief-widget"

if (-not (Test-Path $source)) {
    throw "Source project not found: $source"
}

New-Item -ItemType Directory -Path $DestinationPath -Force | Out-Null

$exclude = @(
    "node_modules",
    "dist"
)

Get-ChildItem -Path $source -Force | Where-Object { $exclude -notcontains $_.Name } | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $DestinationPath -Recurse -Force
}

Write-Host "Copied experience-builder-station-brief-widget project to $DestinationPath"
Write-Host "Next: initialize git there, review README/PUBLISHING.md, and push to a new repository."