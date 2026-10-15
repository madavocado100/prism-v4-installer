param(
    [string]$InstallDir,
    [switch]$Uninstall,
    [switch]$NoShortcuts,
    [string]$ShortcutRoot
)
$ErrorActionPreference = 'Stop'
if (-not $InstallDir) {
    if (-not $env:LOCALAPPDATA) { throw 'Run on Windows or specify -InstallDir with -NoShortcuts for payload validation.' }
    $InstallDir = Join-Path $env:LOCALAPPDATA 'PrismV4Desktop'
}
$root = Split-Path -Parent $PSScriptRoot
$files = @('rgb-audio-visualizer-v4.html', 'launch-windows.ps1', 'README.md', 'config/default.json')
$links = @()
if (-not $NoShortcuts) {
    $desktop = [Environment]::GetFolderPath('Desktop')
    $programs = [Environment]::GetFolderPath('Programs')
    if ($ShortcutRoot) { $desktop = Join-Path $ShortcutRoot 'Desktop'; $programs = Join-Path $ShortcutRoot 'Programs' }
    $links += Join-Path $desktop 'PRISM v4 Desktop Audio.lnk'
    $links += Join-Path $programs 'PRISM v4 Desktop Audio.lnk'
}
if ($Uninstall) {
    foreach ($name in $files) {
        $target = Join-Path $InstallDir $name
        if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Force }
    }
    foreach ($link in $links) { if (Test-Path -LiteralPath $link) { Remove-Item -LiteralPath $link -Force } }
    foreach ($dir in @((Join-Path $InstallDir 'config'), $InstallDir)) {
        if ((Test-Path -LiteralPath $dir) -and -not (Get-ChildItem -LiteralPath $dir -Force)) { Remove-Item -LiteralPath $dir }
    }
    Write-Output 'Uninstalled Prism v4 Desktop Audio; browser settings and other files preserved.'
    exit 0
}
if ([IO.Path]::GetFullPath($root) -eq [IO.Path]::GetFullPath($InstallDir)) { throw 'Extract and run the distribution outside the install directory.' }
foreach ($name in $files) {
    $target = Join-Path $InstallDir $name
    New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $root $name) -Destination $target -Force
    # The installer has explicit user authorization to install these bundled scripts.
    if ($env:OS -eq 'Windows_NT') { Unblock-File -LiteralPath $target -ErrorAction SilentlyContinue }
}
if (-not $NoShortcuts) {
    $shell = New-Object -ComObject WScript.Shell
    foreach ($link in $links) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $link) -Force | Out-Null
        $shortcut = $shell.CreateShortcut($link)
        $shortcut.TargetPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
        $shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $InstallDir 'launch-windows.ps1') + '"'
        $shortcut.WorkingDirectory = $InstallDir
        $shortcut.Description = 'PRISM v4 Desktop Audio'
        $shortcut.Save()
    }
}
Write-Output "Installed $InstallDir"
