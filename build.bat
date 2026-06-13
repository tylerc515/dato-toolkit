@echo off
setlocal

set PYTHON=python
if exist ".venv\Scripts\python.exe" set PYTHON=.venv\Scripts\python.exe

"%PYTHON%" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name "TraceTrackerBuilder" ^
    --icon "assets\icon.ico" ^
    main.py

endlocal
