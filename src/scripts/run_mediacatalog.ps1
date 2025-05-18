


Write-Host "DEBUG: PSScriptRoot is $PSScriptRoot"



$scriptsDir = $PSScriptRoot
$srcDir = Split-Path -Path $scriptsDir -Parent
$projectPath = Split-Path -Path $srcDir -Parent

Write-Host "DEBUG: Calculated srcDir: $srcDir"
Write-Host "DEBUG: Calculated projectPath: $projectPath"

$venvName = "venv"
$pythonScriptName = "MediaCatalog.py"


$venvPythonPath = Join-Path -Path $projectPath -ChildPath (Join-Path -Path $venvName -ChildPath "Scripts\python.exe")
$fullScriptPath = Join-Path -Path $projectPath -ChildPath $pythonScriptName

Write-Host "DEBUG: venvPythonPath: $venvPythonPath"
Write-Host "DEBUG: fullScriptPath: $fullScriptPath"



if (-not (Test-Path $projectPath -PathType Container)) {
    Write-Error "FATAL: Calculated project root path does not exist or is not a directory: '$projectPath'"
    Start-Sleep -Seconds 10
    exit 1
}
if (-not (Test-Path $fullScriptPath -PathType Leaf)) {
    Write-Error "FATAL: Python script not found: '$fullScriptPath'"
    $errorLogPath = Join-Path -Path $projectPath -ChildPath "powershell_launch_error.log"
    "$(Get-Date): Python script not found at '$fullScriptPath'. Calculated projectPath was '$projectPath'." | Out-File -FilePath $errorLogPath -Append
    Start-Sleep -Seconds 10
    exit 1
}
if (-not (Test-Path $venvPythonPath -PathType Leaf)) {
    Write-Error "FATAL: Virtual environment Python not found: '$venvPythonPath'."
    $errorLogPath = Join-Path -Path $projectPath -ChildPath "powershell_launch_error.log"
    "$(Get-Date): Virtual environment Python not found at '$venvPythonPath'. Calculated projectPath was '$projectPath'." | Out-File -FilePath $errorLogPath -Append
    Start-Sleep -Seconds 10
    exit 1
}


Write-Host "Attempting to launch Media Catalog Bot in the background..."
Write-Host "Project Root: `"$projectPath`""
Write-Host "Python (venv): `"$venvPythonPath`""
Write-Host "Script: `"$fullScriptPath`""
$logFilePathInProjectData = Join-Path -Path "data" -ChildPath "mediabot.log"
$fullBotLogPath = Join-Path -Path $projectPath -ChildPath $logFilePathInProjectData
Write-Host "Bot logs will be in '$fullBotLogPath'"
Write-Host "---"

try {

    $argumentList = "-u `"$fullScriptPath`""



    $process = Start-Process -FilePath $venvPythonPath -ArgumentList $argumentList -WorkingDirectory $projectPath -WindowStyle Hidden -PassThru
    

    Start-Sleep -Seconds 1
    if ($process.HasExited) {
        Write-Warning "Python process started but exited quickly. Exit Code: $($process.ExitCode)."
        Write-Warning "Check '$fullBotLogPath' and 'powershell_launch_error.log' for details."


        $errorLogPath = Join-Path -Path $projectPath -ChildPath "powershell_launch_error.log"
        "$(Get-Date): Python process for '$fullScriptPath' exited quickly. Exit Code: $($process.ExitCode)." | Out-File -FilePath $errorLogPath -Append

        if (-not $env:WT_SESSION) {
            Start-Sleep -Seconds 5
        }
    } else {
        Write-Host "---"
        Write-Host "Media Catalog Bot has been launched in the background."
        Write-Host "To stop the bot, you may need to find and terminate the 'python.exe' process running 'MediaCatalog.py' via Task Manager,"
        Write-Host "or use a dedicated stop script if you create one."
    }

} catch {
    Write-Error "Failed to start Python script '$fullScriptPath' in the background."
    Write-Error "Error: $($_.Exception.Message)"
    $errorLogPath = Join-Path -Path $projectPath -ChildPath "powershell_launch_error.log"
    "$(Get-Date): Error launching bot: $($_.Exception.Message)" | Out-File -FilePath $errorLogPath -Append
    Start-Sleep -Seconds 10
    exit 1
}


exit 0