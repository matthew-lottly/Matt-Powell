Write-Host "Portfolio checks"

$requiredFiles = @(
    "README.md",
    "things-to-do.md",
    "ROADMAP.md",
    "CHANGELOG.md",
    "CONTRIBUTOR_ONBOARDING.md",
    "docs/portfolio-matrix.md",
    "docs/todo-hub.md",
    "docs/todo-standalone-repos.md",
    "docs/todo-github-ops.md",
    "docs/issue-filing-queue.md",
    "docs/issue-filing-tracker.md",
    "docs/issue-opening-batches.md",
    "docs/issue-bodies-showcase.md",
    "docs/issue-bodies-supporting.md",
    "docs/issue-submissions/README.md",
    "docs/pr2-github-cleanup.md",
    "docs/weekly-maintenance-checklist.md",
    "docs/merge-checklist.md",
    ".github/CODEOWNERS",
    ".github/PULL_REQUEST_TEMPLATE.md"
)

$missing = @()
foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        $missing += $file
    }
}

if ($missing.Count -gt 0) {
    Write-Error ("Missing required portfolio files: " + ($missing -join ", "))
    exit 1
}

Write-Host "Required files present."

$matrixProjects = @(
    "arroyo-flood-forecasting-lab",
    "causal-lens",
    "environmental-monitoring-analytics",
    "environmental-monitoring-api",
    "environmental-time-series-lab",
    "experience-builder-station-brief-widget",
    "geoprompt",
    "gulf-coast-inundation-lab",
    "monitoring-anomaly-detection",
    "monitoring-data-warehouse",
    "open-web-map-operations-dashboard",
    "postgis-service-blueprint",
    "qgis-operations-workbench",
    "raster-monitoring-pipeline",
    "spatial-data-api",
    "station-forecasting-workbench",
    "station-risk-classification-lab",
    "strata",
    "tsuan"
)

$matrix = Get-Content -Raw "docs/portfolio-matrix.md"
$missingProjects = @()
foreach ($project in $matrixProjects) {
    if ($matrix -notmatch [regex]::Escape($project)) {
        $missingProjects += $project
    }
}

if ($missingProjects.Count -gt 0) {
    Write-Error ("Missing projects in portfolio matrix: " + ($missingProjects -join ", "))
    exit 1
}

Write-Host "Portfolio matrix includes all tracked projects."
Write-Host "Checks complete."