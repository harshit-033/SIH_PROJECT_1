@echo off
title SIH Local AI Server
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
    .\.venv\Scripts\python.exe run_server.py
) else (
    python run_server.py
)
pause
