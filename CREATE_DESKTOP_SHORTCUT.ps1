$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$exePath = Join-Path $projectDir "dist\Oximata.exe"

if (-not (Test-Path $exePath)) {
    Write-Host "Δεν βρέθηκε το dist\Oximata.exe."
    Write-Host "Τρέξε πρώτα το BUILD_EXE.bat."
    Read-Host "Πάτα Enter για έξοδο"
    exit 1
}

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Οχήματα.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $exePath
$shortcut.WorkingDirectory = Split-Path -Parent $exePath
$shortcut.Description = "Οχήματα - Διαχείριση Στόλου"
$shortcut.Save()

Write-Host "Έτοιμο. Δημιουργήθηκε συντόμευση στην Επιφάνεια Εργασίας:"
Write-Host $shortcutPath
Read-Host "Πάτα Enter για έξοδο"
