# Informes de inspecciones de equipos

Aplicacion web (Streamlit + Python) para sacar informes sobre la parte de
inspecciones / certificacion de equipos del sistema, conectando a la base
**SQL Anywhere `dbemicar12`** del servidor PowerBuilder.

## 1. Requisitos

- Python 3.11 (ya instalado en esta maquina, 64-bit).
- **Driver cliente de SQL Anywhere** instalado y de la **misma arquitectura que
  Python**. Este es el punto critico: ver seccion "Driver" mas abajo.

## 2. Instalacion

```powershell
cd informes_inspecciones
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Configurar credenciales en `.env` (ya viene con los datos de `Config SYBASE.txt`).

## 3. Driver SQL Anywhere

Ya esta instalado el **cliente SQL Anywhere 12 de 64 bits** (driver ODBC
`C:\Program Files\SQL Anywhere 12\Bin64\dbodbc12.dll`), que coincide con el
Python 64-bit. La app conecta con `DRIVER=SQL Anywhere 12;HOST=192.168.0.18:2638;...`
(sin depender del DSN), segun `.env`.

Probar la conexion:

```powershell
.\.venv\Scripts\python.exe test_conexion.py
```

Debe imprimir `[OK] Conectado a base 'dbemicar12'...`.

## 4. Ejecutar la app

Doble clic en **`iniciar.bat`** (levanta el servidor de red en el puerto 8501),
o desde PowerShell:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

- En este equipo: `http://localhost:8501`
- Desde otras PC de la red: `http://172.16.5.197:8501`  (IP de este equipo)

El puerto 8501 ya esta habilitado en el Firewall de Windows (regla
"Streamlit Informes Inspecciones (8501)", perfiles Domain/Private).

## 5. Estructura

- `config.py` - lee la conexion desde `.env`.
- `db.py` - conexion pyodbc y helpers de consulta / introspeccion.
- `test_conexion.py` - prueba de conexion por linea de comandos.
- `app.py` - app Streamlit: pestañas **Inspecciones**, Explorar base y Consulta SQL.
- `reportes/datos.py` - consultas de negocio del informe de inspecciones.
- `reportes/excel.py`, `reportes/pdf.py` - exportacion generica a Excel y PDF.
- `reportes/certificados.py` - genera los PDF oficiales por equipo
  (Informe Preliminar y Certificacion Periodica) replicando los reportes de PowerBuilder.
- `reportes/plantillas_config.py` - textos fijos y firmantes de esos PDF (editable).
- `assets/` - logos (American Advisor, AAD, OAA) usados en los PDF.
- `iniciar.bat` - lanzador del servidor de red.
- `.streamlit/config.toml` - configuracion del servidor web.

### PDF oficiales por equipo

En la pestaña **Detalle inspección**, al abrir cada equipo hay dos botones:
- **Informe Preliminar (PDF)** - replica "INFORME PRELIMINAR DE INSPECCION".
- **Certificación Periódica (PDF)** - replica "CERTIFICACION DE INSPECCION PERIODICA".

Los datos salen de `informe_preliminar` (+ `solicitud_servicio`, `clientes`, `equipos`,
`tiposresultado`). Los textos fijos (encabezado de empresa, legislación, testigo
"presenció las pruebas", Gerente Técnico, códigos de revisión) están en
`reportes/plantillas_config.py` porque en el sistema original estaban dentro del
reporte de PowerBuilder, no en la base.

Además, un botón **"Descargar todos los certificados (ZIP)"** arma un .zip con el
Informe Preliminar y la Certificación de cada equipo de la inspección.

### Informes

La pestaña **Informes** permite elegir:
- **Equipos por empresa**: todos los equipos inspeccionados de una empresa.
- **Próximos a vencer**: equipos cuyo `VTO_INSPECCION` vence dentro de N días
  (cantidad configurable), opcionalmente filtrado por empresa.

Ambos se ven en pantalla y se **descargan en PDF**. Si la empresa tiene **email
cargado** (`clientes.EMAIL`), aparece la opción **Enviar por mail** (adjunta el PDF).

El envío usa el **relay SMTP** de la empresa (`reportes/correo.py`, valores tomados de
`smtp.txt`: `smtp-relay.gmail.com:465`, remitente `no_reply@americanad.com.ar`). El relay
autentica por IP (sin usuario/clave); si hiciera falta, se pueden definir `SMTP_USER` y
`SMTP_PASS` en `.env`. El envío funciona desde la red/IP habilitada en Google Workspace.

### Cargar inspección (escribe en producción)

La pestaña **Cargar inspección** da de alta una inspección nueva
(`solicitud_servicio` + `solicitud_servicio_det` + `informe_preliminar`) dentro de
una transacción. La numeración sigue el patrón del sistema: `IDSOLICITUD = MAX+1`
y `NUM = IDSOLICITUD` (no hay autoincrement ni tabla de numeración; el trigger de
INSERT solo audita). Flujo: completar cabecera (cliente, servicio, fecha, vto,
usuario) → agregar uno o más equipos a la lista → tildar la confirmación →
"Crear inspección". **Escribe en la base real**, por eso pide confirmación expresa.
Tras crearla, ofrece descargar el **Informe Preliminar (PDF)** de cada equipo con los
datos cargados (los campos que falten quedan en blanco y se completan después).

### Editar / estado (escribe en producción)

La pestaña **Editar / estado** lista los equipos inspeccionados con filtros por
empresa, fecha, inspector y estado, y permite editar en una grilla: **estado**
(Pendiente / Favorable / Desfavorable), **oblea, marca, nº de serie, matrícula,
vto. inspección e inspector**. "Guardar cambios" hace `UPDATE` sobre
`informe_preliminar` (con confirmación). El trigger de la tabla audita los cambios.
Al guardar valida **oblea duplicada** (no permite repetir una oblea ya usada en otra
inspección). Debajo, un bloque **"Emitir documentos"** permite descargar, por equipo,
el **Informe Preliminar** y la **Certificación Periódica** (conviene guardar antes).

Además, en **Detalle inspección** se puede **anular** (baja lógica, `ACTIVO=0`) o
**reactivar** una inspección. En la grilla de **Editar / estado** hay una columna
**Activa**: destildarla anula la inspección (y volver a tildarla la reactiva) al guardar.

En **Cargar inspección**, el expander "➕ Agregar provincia o localidad nueva" permite
dar de alta provincias y localidades que no estén en las listas. La fuente **Lato**
viene **empaquetada localmente** (`static/fonts/`, servida por Streamlit) — no depende
de internet.

### Formularios en blanco (para llevar a la inspección)

La pestaña **Formularios** genera, eligiendo un equipo, dos PDF en blanco para
completar a mano en el campo:
- **Informe Preliminar (en blanco)**: el formato del informe con el nombre del equipo
  y las normas/procedimiento ya impresos y el resto de los campos vacíos.
- **Checklist / Hoja de campo**: la lista de verificación del tipo de equipo
  (`hojacampo` + `hojacampo_grupo` + `hojacampo_item`), agrupada, con columnas
  SD / DL / DG / N/A y Observaciones para marcar cada ítem.

## 6. Modelo de datos (inspecciones de equipos)

El servicio **"Inspeccion de Equipos"** es `servicios.IDSERVICIO = 1`
(el `2`, "Certificacion de Personas", es otro modulo).

- `solicitud_servicio`     -> evento de inspeccion (NUM, FECHA, VTO/vencimiento, IDCLIENTE, IDSERVICIO).
- `solicitud_servicio_det` -> equipos inspeccionados en cada solicitud (IDEQUIPO, marca, modelo, año, localidad).
- `equipos`                -> maestro de equipos (DESCRIPCION, NORMA_IRAM).
- `clientes`               -> razon social del cliente.
- `provincias` / `localidades` -> ubicacion.

El informe muestra **una fila por equipo inspeccionado**, con filtros por servicio,
rango de fechas, cliente, equipo y provincia; KPIs (inspecciones, equipos, clientes,
proximos a vencer), graficos (por mes, por equipo, por cliente) y exportacion a
Excel y PDF.

## 7. Migración a MySQL (en curso)

El proyecto puede operar contra **SQL Anywhere** o **MySQL**, según `DB_ENGINE` en `.env`
(`anywhere` | `mysql`). Toda la capa de datos pasa por `db.py`, que adapta el SQL al motor
(`?`→`%s`, `CAST AS BIGINT/INTEGER`→`SIGNED`, `TOP n`→`LIMIT n`).

- **Migrar/sincronizar datos** SQL Anywhere → MySQL (módulo inspección de equipos):
  `python -m migracion.migrar_mysql` (lee de Anywhere por ODBC, recrea y recarga ~17 tablas
  en MySQL; es re-ejecutable, sirve como sync de transición). Config MySQL en `.env`
  (`MYSQL_HOST/PORT/USER/PASSWORD/DB`).
- En desarrollo se usa un **MySQL 9.6 local** (servicio `MySQL`, puerto **3307** para no
  chocar con un MySQL 5.7 preexistente en 3306).
- Para correr la app contra MySQL: poner `DB_ENGINE=mysql` en `.env`.

Pendiente: deploy en VPS DigitalOcean (Managed MySQL + nginx + HTTPS + login) y la sync
periódica programada desde la red local.

## 8. Dejar la app siempre encendida (opcional)

Para que arranque sola al iniciar Windows, crear una Tarea Programada que ejecute
`iniciar.bat` al inicio de sesion / arranque del equipo (Programador de tareas de
Windows). Si se requiere control de acceso por usuario, se puede agregar un login.
