[CmdletBinding()]
param(
    [string]$OutputRoot = "output/submission",
    [switch]$IncludeCheckpoint,
    [switch]$NoArchive
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$reportDir = Join-Path $projectRoot "output/doc"
$requiredArtifacts = @(
    "TraceGuard_作品报告_工作稿.docx",
    "TraceGuard_作品报告_工作稿.pdf",
    "TraceGuard_原创性声明_待签章.docx",
    "TraceGuard_原创性声明_待签章.pdf"
)

foreach ($name in $requiredArtifacts) {
    $path = Join-Path $reportDir $name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required submission artifact not found: $path"
    }
}

$outputBase = if ([System.IO.Path]::IsPathRooted($OutputRoot)) {
    [System.IO.Path]::GetFullPath($OutputRoot)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $projectRoot $OutputRoot))
}
New-Item -ItemType Directory -Force -Path $outputBase | Out-Null

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$packageName = "TraceGuard_submission_working_$stamp"
$packageDir = Join-Path $outputBase $packageName
$programDir = Join-Path $packageDir "program"
$materialsDir = Join-Path $packageDir "materials"
New-Item -ItemType Directory -Path $programDir, $materialsDir | Out-Null

$trackedFiles = & git -C $projectRoot ls-files
if ($LASTEXITCODE -ne 0) {
    throw "Unable to enumerate tracked source files"
}
foreach ($relativePath in $trackedFiles) {
    $source = Join-Path $projectRoot $relativePath
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        continue
    }
    $destination = Join-Path $programDir $relativePath
    $destinationParent = Split-Path -Parent $destination
    New-Item -ItemType Directory -Force -Path $destinationParent | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination
}

foreach ($name in $requiredArtifacts) {
    Copy-Item -LiteralPath (Join-Path $reportDir $name) -Destination $materialsDir
}

$manifestLines = @(
    "TraceGuard working submission package",
    "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')",
    "Git commit: $(& git -C $projectRoot rev-parse HEAD)",
    "Status: NOT FINAL - teammate evidence, cover fields, handwritten signatures, stamp and liaison upload remain pending.",
    ""
)

if ($IncludeCheckpoint) {
    $checkpointSource = @(
        (Join-Path $projectRoot "checkpoints/best.pth"),
        (Join-Path $projectRoot "best.pth")
    ) | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if (-not $checkpointSource) {
        throw "Checkpoint not found in checkpoints/best.pth or best.pth"
    }
    $checkpointDir = Join-Path $programDir "checkpoints"
    New-Item -ItemType Directory -Force -Path $checkpointDir | Out-Null
    $checkpointTarget = Join-Path $checkpointDir "best.pth"
    Copy-Item -LiteralPath $checkpointSource -Destination $checkpointTarget
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $checkpointTarget).Hash
    $manifestLines += "Checkpoint: program/checkpoints/best.pth"
    $manifestLines += "Checkpoint SHA-256: $hash"
} else {
    $manifestLines += "Checkpoint: NOT INCLUDED; rerun with -IncludeCheckpoint for an offline runnable package."
}

$manifestLines += ""
$manifestLines += "Materials:"
foreach ($name in $requiredArtifacts) {
    $artifact = Join-Path $materialsDir $name
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $artifact).Hash
    $manifestLines += "- materials/$name | SHA-256 $hash"
}
$manifestLines | Set-Content -LiteralPath (Join-Path $packageDir "PACKAGE_STATUS.txt") -Encoding utf8

if (-not $NoArchive) {
    $archivePath = "$packageDir.zip"
    Compress-Archive -Path (Join-Path $packageDir "*") -DestinationPath $archivePath -CompressionLevel Optimal
    Write-Output $archivePath
} else {
    Write-Output $packageDir
}
