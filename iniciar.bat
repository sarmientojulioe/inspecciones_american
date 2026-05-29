@echo off
REM Inicia la app de informes de inspecciones en modo servidor de red.
cd /d "%~dp0"
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
pause
