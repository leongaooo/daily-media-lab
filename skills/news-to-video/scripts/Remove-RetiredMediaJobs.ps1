[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$JobsRoot,
    [Parameter(Mandatory)]
    [string]$NewJob,
    [string]$Output,
    [string]$VideoName = 'video.mp4',
    [string[]]$RetiredJob = @(),
    [switch]$Apply
)

$ErrorActionPreference = 'Stop'

function Get-PlainDirectory([string]$Path) {
    $directory = Get-Item -LiteralPath $Path -Force
    if (-not ($directory -is [IO.DirectoryInfo]) -or
        ($directory.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Expected a normal directory: $Path"
    }
    return $directory
}

function Get-JobDate([IO.DirectoryInfo]$DayDirectory) {
    return [datetime]::ParseExact(
        $DayDirectory.Name, 'yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture
    )
}

$root = Get-PlainDirectory $JobsRoot
if ($root.Name -ne 'jobs') {
    throw "Expected the media jobs root: $($root.FullName)"
}
for ($ancestor = $root.Parent; $ancestor; $ancestor = $ancestor.Parent) {
    $null = Get-PlainDirectory $ancestor.FullName
}
$current = Get-PlainDirectory $NewJob
$currentDay = Get-PlainDirectory $current.Parent.FullName
if ($currentDay.Parent.FullName -ne $root.FullName) {
    throw "New job must be inside jobs/YYYY-MM-DD/<episode-id>: $($current.FullName)"
}
$cutoff = Get-JobDate $currentDay

# The render receipt identifies the completed MP4. A draft, incomplete render, or
# receipt copied from another job must never trigger retirement.
$outputDirectory = if ($Output) {
    Get-PlainDirectory $Output
} else {
    Get-PlainDirectory (Join-Path $current.FullName 'output')
}
$currentPrefix = $current.FullName + [IO.Path]::DirectorySeparatorChar
if (-not $outputDirectory.FullName.StartsWith($currentPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Output must be inside the new job: $($outputDirectory.FullName)"
}
for ($ancestor = $outputDirectory.Parent; $ancestor.FullName -ne $current.FullName; $ancestor = $ancestor.Parent) {
    $null = Get-PlainDirectory $ancestor.FullName
}
if ($VideoName -notmatch '^[^\\/:*?"<>|]+\.mp4$') {
    throw "VideoName must be an MP4 file name: $VideoName"
}
$report = Get-Item -LiteralPath (Join-Path $outputDirectory.FullName 'validation.json') -Force
$video = Get-Item -LiteralPath (Join-Path $outputDirectory.FullName $VideoName) -Force
foreach ($artifact in @($report, $video)) {
    if (-not ($artifact -is [IO.FileInfo]) -or
        ($artifact.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Expected a normal render artifact: $($artifact.FullName)"
    }
}
$validation = Get-Content -LiteralPath $report.FullName -Raw -Encoding utf8 | ConvertFrom-Json
$identity = $validation.artifacts.$VideoName
if ($validation.full_decode_passed -isnot [bool] -or -not $validation.full_decode_passed -or
    $video.Length -le 0 -or $video.Length -ne $identity.bytes -or
    $video.FullName -ne $identity.path -or
    (Get-FileHash -LiteralPath $video.FullName).Hash -ne $identity.sha256) {
    throw "A verified completed render is required: $($video.FullName)"
}

$olderJobs = @(
    foreach ($day in (Get-ChildItem -LiteralPath $root.FullName -Directory -Force)) {
        if ($day.Attributes -band [IO.FileAttributes]::ReparsePoint) { continue }
        try { $dayDate = Get-JobDate $day }
        catch [FormatException] { continue }
        if ($dayDate -ge $cutoff) { continue }
        Get-ChildItem -LiteralPath $day.FullName -Directory -Force |
            Where-Object { -not ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) }
    }
)

if (-not $Apply) {
    $olderJobs | Select-Object -ExpandProperty FullName
    return
}

# The workflow checks references and gives only the exact jobs it has retired.
# Validate all requested paths before deleting the first one.
$retired = @(
    foreach ($path in ($RetiredJob | Select-Object -Unique)) {
        $job = Get-PlainDirectory $path
        if ($job.FullName -notin $olderJobs.FullName) {
            throw "Outside the eligible older jobs: $($job.FullName)"
        }
        $job
    }
)
foreach ($job in $retired) {
    $null = Get-PlainDirectory $job.Parent.FullName
    $lockPath = Join-Path $job.Parent.FullName ".$($job.Name).media-production.lock"
    try {
        $lock = [IO.File]::Open($lockPath, [IO.FileMode]::CreateNew)
    } catch [IO.IOException] {
        Write-Warning "Skipped $($job.FullName): cannot acquire $lockPath"
        continue
    }
    try {
        $null = Get-PlainDirectory $job.FullName
        $blocker = Get-ChildItem -LiteralPath $job.FullName -Recurse -Force |
            Where-Object {
                ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
                $_.Name -eq 'LOCK' -or $_.Name -like '*.lock'
            } |
            Select-Object -First 1
        if ($blocker) {
            Write-Warning "Skipped $($job.FullName): link or lock at $($blocker.FullName)"
            continue
        }

        Remove-Item -LiteralPath $job.FullName -Recurse -Force
        if (Test-Path -LiteralPath $job.FullName) {
            throw "Job still exists after cleanup: $($job.FullName)"
        }
        [pscustomobject]@{ Removed = $job.FullName }
    } finally {
        $lock.Dispose()
        Remove-Item -LiteralPath $lockPath
    }
}
