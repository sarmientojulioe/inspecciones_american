# Deploy en DigitalOcean (módulo Inspección de Equipos)

La app corre contra **MySQL** en la nube (`DB_ENGINE=mysql`). En la VPS **no se usa
SQL Anywhere ni pyodbc** (pyodbc queda como dependencia solo-Windows). Los datos se
cargan con el script de migración corriendo **on-prem** (que tiene acceso a la LAN) y
escribiendo hacia el MySQL administrado.

## 1. Base: Managed MySQL (DigitalOcean)

1. Crear un **Managed Database → MySQL** en DigitalOcean.
2. En *Trusted Sources*, habilitar la **IP pública de la red on-prem** (para poder cargar
   datos) y la app (App Platform/droplet) que la consumirá.
3. Anotar host, puerto (25060), usuario, contraseña, base y descargar el **CA cert**
   (la conexión exige SSL).

## 2. Cargar / sincronizar datos (desde on-prem)

En la máquina on-prem (la que ve SQL Anywhere), apuntar el `.env` al MySQL administrado:

```
MYSQL_HOST=<host-do>.db.ondigitalocean.com
MYSQL_PORT=25060
MYSQL_DB=emicar_insp
MYSQL_USER=<usuario>
MYSQL_PASSWORD=<clave>
```

> El Managed MySQL exige SSL: agregar a `migracion/migrar_mysql.py` (en `mysql_config`)
> `ssl={"ca": "<ruta-al-ca-certificate.crt>"}` para la conexión.

Ejecutar `python -m migracion.migrar_mysql` para la carga inicial. Para la **sync de
transición**, programarlo (Programador de tareas de Windows) cada X horas hasta el cutover.

## 3a. App en DigitalOcean App Platform (recomendado)

1. **Create → Apps → GitHub** y elegir `sarmientojulioe/inspecciones_american`, rama `main`.
2. Componente **Web Service** (Python). Run command (ya está en `Procfile`):
   `streamlit run app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true`
3. **Environment variables**: `DB_ENGINE=mysql`, `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DB`,
   `MYSQL_USER`, `MYSQL_PASSWORD` (y opcional `SMTP_USER`/`SMTP_PASS`).
4. HTTPS y dominio los maneja App Platform automáticamente.

## 3b. App en un Droplet (alternativa)

1. Droplet Ubuntu; `git clone` del repo; `python3 -m venv .venv`; `pip install -r requirements.txt`.
2. Crear `/etc/systemd/system/inspecciones.service` que ejecute el comando del `Procfile`
   (con `--server.port 8501`) y las variables de entorno (`DB_ENGINE=mysql`, `MYSQL_*`).
3. **nginx** como reverse proxy a `127.0.0.1:8501` (con `proxy_set_header Upgrade`/`Connection`
   para websockets) y **certbot** para HTTPS. Abrir 80/443 en el firewall.

## 4. Acceso (login)

La app ya pide **usuario y clave** validando contra `LICUSUARIO` (los mismos usuarios del
sistema). En la VPS valida contra la tabla `licusuario` migrada a MySQL.

## 5. Cutover

Cuando se deje de usar el PowerBuilder, detener la sync: el MySQL pasa a ser la única
fuente de verdad y la app escribe directamente ahí.
