@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo ClipboardPlus environment is missing. Run setup.bat first.
  pause
  exit /b 1
)
call "%~dp0start_zhumi_memo.bat"
endlocal
