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

## 4b. Sync manual por volcado (modo elegido)

El MySQL de Easypanel es **interno** (no expuesto). La actualización se hace por volcado:

1. En la máquina on-prem, ejecutar **`actualizar_dump.bat`** (o `python -m migracion.generar_dump`)
   → genera `inspecciones_american.sql.gz` leyendo de SQL Anywhere.
2. En phpMyAdmin, base `inspecciones_american` → **Importar** ese `.sql.gz`.

> **Importante (evitar pérdida de datos):** el dump hace DROP + CREATE + recarga, es decir
> **pisa** el contenido del MySQL con lo que hay en SQL Anywhere. Durante la transición, la
> **fuente de verdad sigue siendo el PowerBuilder/SQL Anywhere**: hacé la carga/edición ahí
> (o en la web, pero entonces NO re-importes el dump, porque borraría esos cambios). Recién en
> el **cutover** se deja de re-importar y la app web pasa a escribir como fuente única.

## 5. Cutover

Cuando se deje de usar el PowerBuilder, detener la sync (no re-importar más): el MySQL pasa
a ser la única fuente de verdad y la app escribe directamente ahí.

## 6. Deploy automático (GitHub → Easypanel)

La app corre en **Easypanel** (Docker, build por `Dockerfile`). El objetivo es que cada
`git push` a la rama **`main`** dispare una reconstrucción automática del servicio, sin tener
que entrar al panel a darle "Deploy" a mano.

Mecanismo: **push a GitHub → GitHub llama un webhook → Easypanel reconstruye el servicio.**

### 6.1. Dominios (ya configurados)

El servidor es la IP `167.71.125.132`. Tanto el panel como la app están expuestos por
**dominio propio con HTTPS válido** (Let's Encrypt), así que el webhook de GitHub funciona
con **SSL verification activado**:

- **App** (servicio): `https://inspecciones.americanad.ar/` — la página pública.
- **Panel** de Easypanel: su propio subdominio HTTPS (`<panel-host>`).

> La URL del Deploy Webhook la sirve el **panel** (`<panel-host>`), **no** el dominio de la
> app. Reemplazar `<panel-host>` por el dominio real del panel donde aparezca abajo.

### 6.2. Fuente del servicio = GitHub

En Easypanel: proyecto → servicio `inspecciones_american` → pestaña **Source**:
- Provider **GitHub**, repo `sarmientojulioe/inspecciones_american`, rama **`main`**.
- Build method: **Dockerfile**.

### 6.3. Webhook de deploy

1. En el servicio → pestaña **Deployments** → sección **Deploy Webhook**, copiar la URL única
   (formato `https://<panel-host>/api/deploy/<TOKEN>`). La sirve el panel, no la app.
   Es secreta (equivale a una clave).
2. En GitHub: repo → **Settings → Webhooks → Add webhook**:
   - **Payload URL:** la URL del paso anterior.
   - **Content type:** `application/json`.
   - **SSL verification:** *Enable* (ya que el dominio tiene HTTPS válido).
   - **Which events:** *Just the push event*.
   - **Active:** ✓ → **Add webhook**.

### 6.4. Probar

Hacer un commit y `git push origin main`. En GitHub → **Webhooks** la entrega debe figurar con
**✅ 200**; en Easypanel → **Deployments** arranca un build nuevo. La página queda actualizada
al terminar el build.

> Seguridad: el token del webhook permite disparar deploys. Si se filtra, regenerarlo en
> Easypanel y actualizar la URL en el webhook de GitHub.
