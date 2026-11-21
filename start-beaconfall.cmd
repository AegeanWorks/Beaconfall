@echo off
cd /d "%~dp0"
python play.py %*
if errorlevel 1 (
    echo.
    echo Beaconfall could not start. Check Python and the Keystone prerequisites in README.md.
    pause
    exit /b 1
)
exit /b 0
