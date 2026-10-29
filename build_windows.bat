@echo off
rem Build GameCheck.exe on Windows. Needs Python 3.10+ from python.org (tick "Add to PATH").
rem Result: dist\GameCheck.exe
cd /d "%~dp0"
python -m pip install -r requirements-dev.txt || goto :error
python -m pytest -q || goto :error
pyinstaller --noconfirm gamecheck.spec || goto :error
dist\GameCheck.exe --report || goto :error
echo.
echo Done: dist\GameCheck.exe
goto :eof
:error
echo Build failed.
exit /b 1
