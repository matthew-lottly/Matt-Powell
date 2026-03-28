<#
.SYNOPSIS
  Convert the Markdown draft to LaTeX and PDF using Pandoc and pdflatex on Windows PowerShell.

.NOTES
  Requires: pandoc on PATH, a LaTeX engine (pdflatex) on PATH. bibtex optional.
#>

$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RootDir = Join-Path $BaseDir ".."
$InputMD = Join-Path $RootDir "strata-paper.md"
$OutTex = Join-Path $BaseDir "manuscript_pandoc.tex"
$OutPdf = Join-Path $BaseDir "manuscript_pandoc.pdf"

Write-Host "Input: $InputMD"
Write-Host "Output: $OutPdf"

if (-not (Get-Command pandoc -ErrorAction SilentlyContinue)) {
    Write-Error 'pandoc not found on PATH. Install pandoc (https://pandoc.org/installing.html) and retry.'
    exit 1
}

if (-not (Test-Path $InputMD)) {
    Write-Error "Input markdown not found: $InputMD"
    exit 1
}

Write-Host "Running pandoc..."
& pandoc $InputMD -s -o $OutTex --standalone --toc --number-sections --lua-filter=./pandoc_filters/include_figures.lua
if ($LASTEXITCODE -ne 0) { Write-Error "pandoc failed."; exit $LASTEXITCODE }

Write-Host "Running pdflatex (1/3)..."
& pdflatex -interaction=nonstopmode -halt-on-error -output-directory $BaseDir $OutTex

if (Get-Command bibtex -ErrorAction SilentlyContinue) {
    Write-Host "Running bibtex..."
    Push-Location $BaseDir
    & bibtex "manuscript_pandoc"
    Pop-Location
} else {
    Write-Host 'bibtex not found - skipping bibliography run'
}

Write-Host "Running pdflatex (2/3)..."
& pdflatex -interaction=nonstopmode -halt-on-error -output-directory $BaseDir $OutTex

Write-Host "Running pdflatex (3/3)..."
& pdflatex -interaction=nonstopmode -halt-on-error -output-directory $BaseDir $OutTex

if (Test-Path $OutPdf) {
    Write-Host "Draft PDF written to: $OutPdf"
} else {
    Write-Error "PDF not produced. Check LaTeX log in $BaseDir for details."
    exit 2
}
