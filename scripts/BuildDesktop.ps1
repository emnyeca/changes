Set-Location "$PSScriptRoot\.."

Write-Host "Installing dependencies..."
python -m pip install -e ".[ui,midi,realtime,sysex]"
if (-not $?) { Write-Error "pip install failed"; exit 1 }

Write-Host "Verifying build environment..."
python scripts\verify_desktop_build.py
if (-not $?) { Write-Error "Build verification failed"; exit 1 }

Write-Host "Building desktop app..."
& .\.venv\Scripts\streamlit-desktop-app.exe build src\changes\main_ui.py `
  --name "EUB Changes" `
  --icon docs\assets\adobe\1x\eub_changes_icon.ico `
  --streamlit-options `
    --theme.base=light `
    --theme.primaryColor="#7E5CC6" `
    --theme.backgroundColor="#FBF7FC" `
    --theme.secondaryBackgroundColor="#F4EEF8" `
    --theme.textColor="#191326" `
    --client.toolbarMode=viewer `
  --pyinstaller-options `
    --onefile `
    --collect-all changes `
    --collect-all digitone_syx_toolkit `
    --copy-metadata digitone-syx-toolkit `
    --collect-all mido `
    --collect-all rtmidi `
    --hidden-import mido.backends.rtmidi `
    --hidden-import rtmidi `
    --add-data "docs\assets\1x;docs\assets\1x" `
    --add-data "LICENSE;." `
    --splash docs\assets\1x\eub_changes_splash_960x540.png `
    --noconsole `
    --noconfirm `
  2>&1
