@echo off
setlocal EnableExtensions
set "HERE=%~dp0"
set "BAT=%HERE%..\desktop\launch_karel.bat"
if exist "%BAT%" (
    call "%BAT%" --python %*
    exit /b %errorlevel%
)
pyw -3 "%HERE%karel.py" %* 2>nul || pythonw "%HERE%karel.py" %*
