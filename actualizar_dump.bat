@echo off
REM Regenera el volcado SQL del modulo de inspecciones (desde SQL Anywhere)
REM para re-importar en el MySQL de Easypanel via phpMyAdmin.
cd /d "%~dp0"
".venv\Scripts\python.exe" -m migracion.generar_dump inspecciones_american.sql.gz
echo.
echo Listo: inspecciones_american.sql.gz
echo Importalo en phpMyAdmin -> base "inspecciones_american".
pause
