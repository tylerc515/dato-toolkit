@echo off
setlocal

set PYTHON=python
if exist ".venv\Scripts\python.exe" set PYTHON=.venv\Scripts\python.exe

"%PYTHON%" scripts\generate_icon.py

"%PYTHON%" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name "DATOToolkit_v2.2.2" ^
    --icon "assets\icon.ico" ^
    --add-data "assets/logo.svg;assets" ^
    --add-data "bsi_logo.jpg;." ^
    main.py

endlocal
