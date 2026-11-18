@echo off
setlocal EnableExtensions
set "HERE=%~dp0"
where python >nul 2>nul && (
    python -B "%HERE%prepare_test_usb.py" %*
    goto :done
)
py -3 -B "%HERE%prepare_test_usb.py" %*
:done
pause
