@echo off
call python -m venv .\venv
call .\venv\Scripts\activate
python -m pip install -r requirements.txt