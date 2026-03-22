param(
    [switch]$ListOnly
)

$ErrorActionPreference = "SilentlyContinue"
$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $rootDir

$candidates = New-Object System.Collections.Generic.List[string]

function Add-Candidate {
    param([string]$PathValue)
    if ([string]::IsNullOrWhiteSpace($PathValue)) { return }
    if (-not (Test-Path $PathValue)) { return }
    $normalized = (Resolve-Path $PathValue).Path
    if (-not $candidates.Contains($normalized)) {
        $candidates.Add($normalized)
    }
}

try {
    $pyLines = py -0p
    foreach ($line in $pyLines) {
        $path = ($line -replace '^-V:[^ ]+\s*\*?\s*', '').Trim()
        Add-Candidate $path
    }
} catch {}

foreach ($name in @("python", "python3")) {
    try {
        $cmd = (Get-Command $name -ErrorAction Stop).Source
        Add-Candidate $cmd
    } catch {}
}

foreach ($pathDir in ($env:Path -split ';')) {
    if ([string]::IsNullOrWhiteSpace($pathDir)) { continue }
    $trimmed = $pathDir.Trim('"').Trim()
    if ([string]::IsNullOrWhiteSpace($trimmed)) { continue }
    Add-Candidate (Join-Path $trimmed "python.exe")
    Add-Candidate (Join-Path $trimmed "python3.exe")
}

foreach ($envPath in @($env:PYTHONHOME, $env:PYTHON_ROOT, $env:PYTHONHOME64)) {
    if ([string]::IsNullOrWhiteSpace($envPath)) { continue }
    Add-Candidate (Join-Path $envPath "python.exe")
    Add-Candidate (Join-Path $envPath "python3.exe")
}

foreach ($regKey in @(
    "HKCU:\Software\Python\PythonCore",
    "HKLM:\Software\Python\PythonCore",
    "HKLM:\Software\WOW6432Node\Python\PythonCore"
)) {
    try {
        if (-not (Test-Path $regKey)) { continue }
        Get-ChildItem $regKey | ForEach-Object {
            $installPath = Join-Path $_.PSPath "InstallPath"
            $defaultPath = (Get-ItemProperty -Path $installPath -ErrorAction SilentlyContinue)."(default)"
            if ($defaultPath) {
                Add-Candidate (Join-Path $defaultPath "python.exe")
            }
            $exePath = (Get-ItemProperty -Path $installPath -ErrorAction SilentlyContinue).ExecutablePath
            if ($exePath) {
                Add-Candidate $exePath
            }
        }
    } catch {}
}

$scanRoots = @(
    "$env:LocalAppData\Programs\Python",
    "$env:ProgramFiles",
    "C:\Python",
    "C:\Program Files\Python",
    "D:\Program Files\Python",
    "E:\Program Files\Python",
    "E:\program files\Python"
)
if ($env:ProgramFiles -ne ${env:ProgramFiles(x86)}) {
    $scanRoots += ${env:ProgramFiles(x86)}
}

try {
    Get-PSDrive -PSProvider FileSystem | ForEach-Object {
        $root = $_.Root.TrimEnd('\')
        foreach ($suffix in @("\Program Files\Python", "\program files\Python", "\Python")) {
            $scanRoots += ($root + $suffix)
        }
    }
} catch {}

$scanRoots = $scanRoots | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique

foreach ($scanRoot in $scanRoots) {
    if ([string]::IsNullOrWhiteSpace($scanRoot)) { continue }
    if (-not (Test-Path $scanRoot)) { continue }
    try {
        Add-Candidate (Join-Path $scanRoot "python.exe")
        Add-Candidate (Join-Path $scanRoot "python3.exe")
        Get-ChildItem -Path (Join-Path $scanRoot "*") -Directory |
            ForEach-Object {
                Add-Candidate (Join-Path $_.FullName "python.exe")
                Add-Candidate (Join-Path $_.FullName "python3.exe")
            }
        Get-ChildItem -Path (Join-Path $scanRoot "Python*") -Directory |
            ForEach-Object {
                Add-Candidate (Join-Path $_.FullName "python.exe")
                Add-Candidate (Join-Path $_.FullName "python3.exe")
                try {
                    Get-ChildItem -Path (Join-Path $_.FullName "Python*") -Directory |
                        ForEach-Object {
                            Add-Candidate (Join-Path $_.FullName "python.exe")
                            Add-Candidate (Join-Path $_.FullName "python3.exe")
                        }
                } catch {}
            }
    } catch {}
}

if ($candidates.Count -eq 0) {
    Write-Host "No Python was found."
    Write-Host "Please install Python 3.10+ and run this script again."
    Write-Host "Download: https://www.python.org/downloads/"
    exit 1
}

$sortedCandidates = $candidates | Sort-Object {
    if ($_ -match "WindowsApps") { 4 }
    elseif ($_ -match "LibreOffice|Git\\usr|msys|cygwin") { 3 }
    elseif ($_ -match "Anaconda|conda|Miniconda") { 2 }
    elseif ($_ -match "\\Python\\Python\d+") { 0 }
    else { 1 }
}, { $_.Length }, { $_ }
$candidates.Clear()
foreach ($candidate in $sortedCandidates) {
    $candidates.Add($candidate) | Out-Null
}

if ($ListOnly) {
    $candidates | ForEach-Object { Write-Output $_ }
    exit 0
}

$pythonExe = $null
if ($candidates.Count -eq 1) {
    $pythonExe = $candidates[0]
} else {
    Write-Host "Multiple Python versions detected. Choose one by number:"
    for ($i = 0; $i -lt $candidates.Count; $i++) {
        Write-Host ("  {0}. {1}" -f ($i + 1), $candidates[$i])
    }
    while ($true) {
        $inputValue = Read-Host "Enter index"
        if ($inputValue -match '^\d+$') {
            $index = [int]$inputValue
            if ($index -ge 1 -and $index -le $candidates.Count) {
                $pythonExe = $candidates[$index - 1]
                break
            }
        }
    }
}

if (-not $pythonExe) {
    Write-Host "Python selection failed."
    exit 1
}

Write-Host ("Selected: {0}" -f $pythonExe)
& $pythonExe --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "The selected Python is not available."
    exit 1
}

if (-not (Test-Path "$rootDir\requirements.txt")) {
    Write-Host "requirements.txt was not found."
    exit 1
}

Write-Host "Installing dependencies..."
& $pythonExe -m pip --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    & $pythonExe -m ensurepip --upgrade | Out-Null
}

& $pythonExe -m pip install -r "$rootDir\requirements.txt"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Dependency installation failed."
    exit 1
}

Write-Host "Dependencies ready. Starting app..."
& $pythonExe "$rootDir\app.py"
exit $LASTEXITCODE
