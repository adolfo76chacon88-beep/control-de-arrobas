# Control de Arrobas

Sistema web (FastAPI + Supabase + HTML/CSS/JS) para registrar arrobas diarias, cerrar cortes y calcular pagos.
**Administrador único:** `adolfo76chacon88@gmail.com`. Los demás usuarios son siempre **LECTOR** y nunca ven dinero.

## Arquitectura (compatible con Vercel)
- `public/` → frontend estático (Vercel lo sirve como sitio estático).
- `api/index.py` → función serverless de Python que expone la app FastAPI (`app/`) bajo `/api/*` (ver `vercel.json`).
- `app/` → backend: `routers/` (API), `services/` (Supabase, cálculos con `Decimal`, PDF con reportlab), `security.py` (auth/roles), `config.py`.
- Un solo despliegue en Vercel; no hace falta separar frontend y backend. El PDF usa reportlab (Python puro, sin binarios del sistema).
- **Seguridad en dos capas:** el backend valida rol en cada endpoint y, además, la BD aplica RLS (el dinero vive en `cut_finance`/`cut_results`, solo admin). El rol lo asigna únicamente un trigger de BD según el correo; no existe ningún endpoint para cambiar roles.

## 1. Abrir en Visual Studio Code
```bash
unzip Control_de_Arrobas_WEB.zip && cd Control_de_Arrobas_WEB
code .
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configurar Supabase (ver también `Control_de_Arrobas_SQL.zip`)
1. Cree un proyecto en https://supabase.com.
2. SQL Editor: ejecute en orden `01_tablas.sql`, `02_funciones_triggers.sql`, `03_rls.sql`, `04_datos_iniciales.sql`.
3. Project Settings → API: copie **URL**, **anon key** y **service_role key**.
4. Authentication → Providers → Email activado. Authentication → URL Configuration: **Site URL** = su dominio de Vercel (y `http://localhost:8000` para pruebas), agréguelos también en *Redirect URLs*.
5. Correo de invitaciones: Authentication → SMTP Settings → use **Resend** (smtp.resend.com, puerto 465, usuario `resend`, contraseña = su API key de Resend) o cualquier SMTP. Las claves se ponen en el panel de Supabase, nunca en el código.
6. Crea al administrador: Authentication → Users → *Add user* con `adolfo76chacon88@gmail.com` y una contraseña (auto-confirm). El trigger le asigna `admin`.

## 3. Ejecutar localmente
```bash
cp .env.example .env     # complete las 3 claves de Supabase
uvicorn app.main:app --reload --port 8000
```
Abra http://localhost:8000. Pruebas de cálculo: `pytest -q`.

## 4. GitHub
```bash
git init && git add . && git commit -m "Control de Arrobas"
git branch -M main
git remote add origin https://github.com/SU_USUARIO/control-de-arrobas.git
git push -u origin main
```
`.env` está en `.gitignore`; nunca suba claves.

## 5. Vercel
1. vercel.com → *Add New Project* → importe el repositorio.
2. Framework Preset: **Other**. No cambie build/output (lo define `vercel.json`).
3. Environment Variables: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SITE_URL` (https://su-app.vercel.app), `ADMIN_EMAIL`.
4. Deploy. Actualizaciones: `git push` redepliega automáticamente.

## Funciones
Trabajadores permanentes (desactivar, no borrar) · cortes con trabajadores reutilizables · registro diario con ½ (3 + 2×½ = 4) y ausencias · resumen por trabajador · FINALIZAR CORTE con precio, media arroba automática y confirmación · bitácora de auditoría al reabrir · historial y comparación de cortes · PDF (admin: diario, resumen, dinero, completo, historial; lector: solo arrobas) · invitaciones/revocación de lectores · mensajes con respuestas y estado pendiente/respondido · notificaciones internas · buscador general · diseño oscuro responsive.

## Dinero
`dinero = arrobas × precio + medias × (precio / 2)` con `Decimal`; se redondea a centavos una sola vez por trabajador (half-up). Ej.: 15 arrobas + 1 media a $12.00 = $186.00. El precio queda guardado por corte (`cut_finance`); cambiar el precio de un corte nuevo nunca altera los anteriores.

## Estado de verificación
Verificado en el entorno de desarrollo: cálculos (½+½=1, 3+2×½=4, $186.00, decimales exactos), PDF (admin con dinero; lector sin dinero y 403 al pedir el de dinero), resumen, ausencias, sintaxis del frontend. **No se pudo ejecutar contra un Supabase real ni levantar FastAPI en el entorno donde se generó** (sin red): ejecute los SQL, `05_pruebas_seguridad.sql`, y haga la prueba de extremo a extremo (login, invitación, cierre de corte) con sus credenciales antes de usarlo en producción.
