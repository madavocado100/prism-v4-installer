$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$tmp = Join-Path ([IO.Path]::GetTempPath()) ('prism installer ' + [guid]::NewGuid())
$installer = Join-Path $root 'installers/windows.ps1'
try {
    & $installer -InstallDir $tmp -NoShortcuts
    foreach ($file in @('rgb-audio-visualizer-v4.html','launch-windows.ps1','config/default.json')) {
        if (-not (Test-Path -LiteralPath (Join-Path $tmp $file))) { throw "Missing payload $file" }
    }
    Set-Content -LiteralPath (Join-Path $tmp 'my-notes.txt') -Value 'keep'
    & $installer -InstallDir $tmp -NoShortcuts
    $parseErrors = $null
    foreach ($script in @($installer, (Join-Path $root 'launch-windows.ps1'))) {
        [void][Management.Automation.Language.Parser]::ParseFile($script,[ref]$null,[ref]$parseErrors)
        if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
    }
    & $installer -InstallDir $tmp -NoShortcuts -Uninstall
    if (-not (Test-Path -LiteralPath (Join-Path $tmp 'my-notes.txt'))) { throw 'Uninstall deleted unrelated files' }
    if (Test-Path -LiteralPath (Join-Path $tmp 'rgb-audio-visualizer-v4.html')) { throw 'Uninstall left app behind' }
    if ($env:OS -eq 'Windows_NT') {
        $linkRoot = Join-Path $tmp 'links'
        & $installer -InstallDir $tmp -ShortcutRoot $linkRoot
        $shell = New-Object -ComObject WScript.Shell
        foreach ($folder in @('Desktop','Programs')) {
            $link = $shell.CreateShortcut((Join-Path $linkRoot ($folder + '/PRISM v4 Desktop Audio.lnk')))
            if (-not (Test-Path -LiteralPath $link.TargetPath)) { throw 'Shortcut target missing' }
            if (-not $link.Arguments.Contains((Join-Path $tmp 'launch-windows.ps1'))) { throw 'Shortcut launches wrong app' }
        }
        & $installer -InstallDir $tmp -ShortcutRoot $linkRoot -Uninstall
        if (Test-Path -LiteralPath (Join-Path $linkRoot 'Desktop/PRISM v4 Desktop Audio.lnk')) { throw 'Uninstall left shortcut behind' }
    }
    Write-Output 'PASS: PowerShell parsing, Windows payload install/update and safe uninstall'
} finally {
    if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force }
}
