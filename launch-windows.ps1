param([switch]$Fullscreen)
$ErrorActionPreference = 'Stop'
$candidates = @()
foreach ($base in @($env:LOCALAPPDATA, $env:ProgramFiles, ${env:ProgramFiles(x86)})) {
    if ($base) {
        $candidates += Join-Path $base 'BraveSoftware\Brave-Browser\Application\brave.exe'
        $candidates += Join-Path $base 'Google\Chrome\Application\chrome.exe'
        $candidates += Join-Path $base 'Microsoft\Edge\Application\msedge.exe'
    }
}
$browser = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $browser) {
    $command = Get-Command brave.exe, chrome.exe, msedge.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command) { $browser = $command.Source }
}
if (-not $browser) { throw 'Install Brave, Chrome or Microsoft Edge to run Prism desktop audio.' }
$uri = ([System.Uri](Join-Path $PSScriptRoot 'rgb-audio-visualizer-v4.html')).AbsoluteUri
$arguments = @('--app="' + $uri + '"', '--class=PrismV4Desktop')
if ($Fullscreen) { $arguments += '--start-fullscreen' }
Start-Process -FilePath $browser -ArgumentList $arguments
