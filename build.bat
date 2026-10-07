@echo off
setlocal

rem Build the portable exe from a throwaway venv so the bundle contains only
rem what requirements.txt installs. PyInstaller follows every import it can
rem resolve, so a build from the global interpreter ships whatever happens to
rem be installed there (numpy rode along that way in v2.6.1).

set PYTHON=python
set VENV=.venv-build

for /f "usebackq tokens=2 delims==" %%v in (`findstr /b __version__ app\__init__.py`) do set VERSION=%%v
set VERSION=%VERSION:"=%
set VERSION=%VERSION: =%
if "%VERSION%"=="" (
    echo Could not read __version__ from app\__init__.py
    exit /b 1
)
set NAME=DATOToolkit_v%VERSION%

echo Creating clean build environment in %VENV%
"%PYTHON%" -m venv --clear "%VENV%" || exit /b 1
"%VENV%\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt || exit /b 1

"%VENV%\Scripts\python.exe" scripts\generate_icon.py || exit /b 1

rem Build outside the Dropbox-synced tree. Dropbox holds the new exe open
rem while PyInstaller embeds the icon, and the build fails with WinError 110.
set WORK=%LOCALAPPDATA%\Temp\dato-toolkit-build
if exist "%WORK%" rmdir /s /q "%WORK%"

"%VENV%\Scripts\python.exe" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name "%NAME%" ^
    --icon "assets\icon.ico" ^
    --add-data "assets/tc_software_logo.png;assets" ^
    --add-data "bsi_logo.jpg;." ^
    --add-data "examples/standard-format/Standard-Sample_Left-to-Right.csv;examples/standard-format" ^
    --distpath "%WORK%\dist" ^
    --workpath "%WORK%\build" ^
    main.py || exit /b 1

if not exist dist mkdir dist
copy /y "%WORK%\dist\%NAME%.exe" "dist\%NAME%.exe" >nul || exit /b 1

echo.
echo Built dist\%NAME%.exe
for %%f in ("dist\%NAME%.exe") do echo Size: %%~zf bytes
echo Warnings: %WORK%\build\%NAME%\warn-%NAME%.txt
endlocal
