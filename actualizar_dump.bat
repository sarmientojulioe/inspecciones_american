@echo off
REM Regenera el volcado SQL del modulo de inspecciones (desde SQL Anywhere).
REM ATENCION: el dump hace DROP + CREATE + recarga. Re-importarlo en MySQL PISA
REM todo lo cargado/editado en la web. Tras el CUTOVER (MySQL = fuente unica) NO
REM debe usarse. Queda solo como referencia historica de la transicion.
cd /d "%~dp0"

echo ============================================================
echo  ADVERTENCIA: CUTOVER HECHO - MySQL es la fuente unica.
echo.
echo  Generar e importar este dump PISARIA (DROP + CREATE + recarga)
echo  todos los datos cargados/editados en la web. Se perderian.
echo ============================================================
echo.
set /p RESP=Escribi SI ENTIENDO para continuar:
if /I not "%RESP%"=="SI ENTIENDO" (
    echo.
    echo Cancelado. No se genero ningun dump.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m migracion.generar_dump inspecciones_american.sql.gz
echo.
echo Listo: inspecciones_american.sql.gz
echo Importalo en phpMyAdmin -^> base "inspecciones_american".
pause
