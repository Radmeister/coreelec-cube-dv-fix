# SPDX-License-Identifier: GPL-2.0-only
# Run on the Windows computer, not inside an SSH session on the Cube.
# Compatible syntax: Windows PowerShell 5.1 and PowerShell 7.
[CmdletBinding()]
param(
    [ValidateSet('check', 'install', 'status', 'rollback')]
    [string]$Action = 'check',
    [string]$CubeAddress = '',
    [string]$CubeLabel = '',
    [string]$ReportsDirectory = ''
)
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$originalSha = 'cde2bace4057ce743d26735a81c8323b21fcce638b1649e4bda309568b683d16'
$fixedSha = '071498095ae2362caaea3ff052b3262fadd904fd37bd607128fc307b517e4b10'

function Invoke-CubeCommand {
    param([string]$Command, [switch]$AllowFailure)
    & $script:sshProgram @script:sshOptions $script:target $Command | Out-Host
    $code = $LASTEXITCODE
    if ($code -ne 0 -and -not $AllowFailure) {
        throw "The Cube command failed (exit $code). No automatic reboot was sent."
    }
    return $code
}

function Copy-CubeFile {
    param([string]$From, [string]$To)
    & $script:scpProgram @script:sshOptions $From $To | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Retrying with the older SCP transfer mode...'
        & $script:scpProgram -O @script:sshOptions $From $To | Out-Host
        if ($LASTEXITCODE -ne 0) { throw 'File transfer failed. Installation stopped.' }
    }
}

try {
    $script:sshProgram = (Get-Command ssh.exe -CommandType Application -ErrorAction Stop).Source
    $script:scpProgram = (Get-Command scp.exe -CommandType Application -ErrorAction Stop).Source
    $payload = Join-Path $PSScriptRoot 'kernel.pq-guard.img'
    $installer = Join-Path $PSScriptRoot 'cube-dv-fix.py'
    if (-not (Test-Path -LiteralPath $payload -PathType Leaf) -or
        -not (Test-Path -LiteralPath $installer -PathType Leaf)) {
        throw 'Extract Cube-DV-Fix-v1.1.zip from Releases and keep its files together. The GitHub Source code ZIP does not contain the kernel.'
    }
    if ((Get-FileHash -LiteralPath $payload -Algorithm SHA256).Hash.ToLowerInvariant() -ne $fixedSha) {
        throw 'The local kernel checksum differs. Download a fresh release package. Nothing uploaded.'
    }
    if (-not $CubeAddress) { $CubeAddress = Read-Host "Cube's IPv4 address (CoreELEC network information)" }
    if ($CubeAddress -notmatch '^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$') {
        throw 'Enter an IPv4 address such as 192.168.1.50.'
    }
    foreach ($part in $CubeAddress.Split('.')) {
        if ([int]$part -gt 255) { throw 'Invalid IPv4 address.' }
    }
    if (-not $CubeLabel) { $CubeLabel = Read-Host 'Label for this Cube [cube]' }
    if (-not $CubeLabel) { $CubeLabel = 'cube' }
    if ($CubeLabel -notmatch '^[A-Za-z0-9_-]+$') { throw 'Use letters, numbers, hyphens or underscores for the label.' }
    if (-not $ReportsDirectory) {
        $ReportsDirectory = Join-Path $HOME 'Downloads/Cube-DV-Fix-Backups'
    }
    $backupDirectory = Join-Path $ReportsDirectory ("{0}-{1}-{2}-{3}" -f $CubeLabel, $CubeAddress, (Get-Date -Format 'yyyyMMdd-HHmmss'), ([guid]::NewGuid().ToString('N').Substring(0, 6)))
    $null = New-Item -ItemType Directory -Path $backupDirectory -Force
    $script:target = "root@$CubeAddress"
    $script:sshOptions = @('-o', 'ConnectTimeout=8')
    Write-Host 'Enter the Cube SSH password when asked. Passwords are not saved.'
    Write-Host 'Windows may ask for the password several times during these transfers.'
    $null = Invoke-CubeCommand 'mkdir -p /storage/Cube-DV-Fix'
    # Copy individual files into a fixed directory; repeated runs cannot nest folders.
    Copy-CubeFile $installer "${script:target}:/storage/Cube-DV-Fix/cube-dv-fix.py"
    Copy-CubeFile $payload "${script:target}:/storage/Cube-DV-Fix/kernel.pq-guard.img"
    $checkCode = Invoke-CubeCommand 'python3 /storage/Cube-DV-Fix/cube-dv-fix.py check' -AllowFailure
    $reportFile = Join-Path $backupDirectory 'check-report.json'
    Copy-CubeFile "${script:target}:/storage/Cube-DV-Fix/check-report.json" $reportFile
    $report = Get-Content -LiteralPath $reportFile -Raw | ConvertFrom-Json
    if ($report.kernel_config_available) {
        Copy-CubeFile "${script:target}:/storage/Cube-DV-Fix/kernel-config.gz" (Join-Path $backupDirectory 'kernel-config.gz')
    }
    Write-Host "Computer reports/backups: $backupDirectory"
    if ($checkCode -ne 0) {
        Write-Host 'Nothing was installed. Keep check-report.json for a matching build.'
        exit $checkCode
    }
    switch ($Action) {
        'check' { Write-Host 'Check finished. No boot files or settings changed.' }
        'status' { $null = Invoke-CubeCommand 'python3 /storage/Cube-DV-Fix/cube-dv-fix.py status' }
        'install' {
            if ($report.status -eq 'ALREADY INSTALLED') {
                Write-Host 'This Cube already has the fixed kernel. Nothing changed.'
                exit 0
            }
            if ($report.status -ne 'READY TO INSTALL') { throw "Install stopped: $($report.status)" }
            $computerBackup = Join-Path $backupDirectory 'kernel.before-install.img'
            Copy-CubeFile "${script:target}:/flash/kernel.img" $computerBackup
            if ((Get-FileHash -LiteralPath $computerBackup -Algorithm SHA256).Hash.ToLowerInvariant() -ne $originalSha) {
                throw 'Computer backup checksum differs. Nothing installed.'
            }
            $null = Invoke-CubeCommand 'python3 /storage/Cube-DV-Fix/cube-dv-fix.py install'
            Copy-CubeFile "${script:target}:/storage/cube-dv-fix-backup/manifest.json" (Join-Path $backupDirectory 'manifest.json')
            Write-Host 'Kernel installed; original verified on both Cube and computer. Requesting reboot.'
            $rebootCode = Invoke-CubeCommand 'sync; systemctl reboot' -AllowFailure
            if ($rebootCode -ne 0) { Write-Host 'Connection closed around reboot. Check the TV for restart.' }
        }
        'rollback' {
            $null = Invoke-CubeCommand 'python3 /storage/Cube-DV-Fix/cube-dv-fix.py rollback'
            Write-Host 'Original kernel restored. Requesting reboot.'
            $rebootCode = Invoke-CubeCommand 'sync; systemctl reboot' -AllowFailure
            if ($rebootCode -ne 0) { Write-Host 'Connection closed around reboot. Check the TV for restart.' }
        }
    }
    exit 0
} catch {
    Write-Host ("STOP: " + $_.Exception.Message) -ForegroundColor Red
    Write-Host 'If ssh.exe or scp.exe is missing, see WINDOWS.md for OpenSSH Client setup.'
    exit 1
}
