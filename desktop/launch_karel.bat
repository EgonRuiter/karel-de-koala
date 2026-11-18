@echo off
setlocal EnableExtensions
set "HERE=%~dp0"
set "NATIVE=%HERE%karel_native.exe"
if not exist "%NATIVE%" set "NATIVE=%HERE%desktop\karel_native.exe"
set "SCRIPT=%HERE%karel.py"
if not exist "%SCRIPT%" set "SCRIPT=%HERE%..\python_extended\karel.py"
if not exist "%SCRIPT%" set "SCRIPT=%HERE%python_extended\karel.py"

echo "%*" | findstr /I /R /C:"--python" /C:"--full" >nul
if not errorlevel 1 if exist "%SCRIPT%" goto :run_python

if exist "%NATIVE%" (
    start "" "%NATIVE%" %*
    exit /b 0
)

:run_python
if not exist "%SCRIPT%" (
    mshta "javascript:alert('Karel de Koala: karel_native.exe niet gevonden naast launch_karel.bat.');close()"
    exit /b 1
)

set "PY_EXE="
set "PY_ARG="
set "PY_CON="

for %%P in (
    "%HERE%pythonw.exe"
    "%HERE%python\pythonw.exe"
    "%HERE%runtime\pythonw.exe"
) do if not defined PY_EXE if exist "%%~P" call :check "%%~P" "" 0

if not defined PY_EXE (
    for /f "usebackq delims=" %%P in (`where pythonw 2^>nul`) do if not defined PY_EXE call :check "%%~P" "" 0
)
if not defined PY_EXE call :check "pyw" "-3" 0
if not defined PY_EXE (
    for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*" "%ProgramFiles%\Python*" "C:\Python*") do (
        if not defined PY_EXE if exist "%%~D\pythonw.exe" call :check "%%~D\pythonw.exe" "" 0
    )
)

if defined PY_EXE (
    start "" "%PY_EXE%" %PY_ARG% "%SCRIPT%" %*
    exit /b 0
)

for %%P in ("%HERE%python.exe" "%HERE%python\python.exe" "%HERE%runtime\python.exe") do (
    if not defined PY_EXE if exist "%%~P" call :check "%%~P" "" 1
)
if not defined PY_EXE (
    for /f "usebackq delims=" %%P in (`where python 2^>nul`) do if not defined PY_EXE call :check "%%~P" "" 1
)
if not defined PY_EXE call :check "py" "-3" 1

if defined PY_EXE (
    set "K_ARGS=%*"
    if defined PY_ARG (
        powershell -NoProfile -WindowStyle Hidden -Command "$a=@($env:PY_ARG,$env:SCRIPT)+@($env:K_ARGS -split ' '|?{$_});Start-Process -WindowStyle Hidden -FilePath $env:PY_EXE -ArgumentList $a"
    ) else (
        powershell -NoProfile -WindowStyle Hidden -Command "$a=@($env:SCRIPT)+@($env:K_ARGS -split ' '|?{$_});Start-Process -WindowStyle Hidden -FilePath $env:PY_EXE -ArgumentList $a"
    )
    exit /b 0
)

mshta "javascript:alert('Karel de Koala: --python gevraagd maar geen Python 3 met Tkinter gevonden.');close()"
exit /b 1

:check
set "CAND=%~1"
set "CARG=%~2"
echo "%CAND%" | findstr /I "WindowsApps" >nul && goto :eof
if defined CARG (
    "%CAND%" %CARG% -c "import tkinter" >nul 2>nul
) else (
    "%CAND%" -c "import tkinter" >nul 2>nul
)
if errorlevel 1 goto :eof
set "PY_EXE=%CAND%"
set "PY_ARG=%CARG%"
set "PY_CON=%~3"
goto :eof
