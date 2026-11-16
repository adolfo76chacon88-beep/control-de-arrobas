import os

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SITE_URL = os.environ.get("SITE_URL", "http://localhost:8000").rstrip("/")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "adolfo76chacon88@gmail.com").lower()
APP_NAME = "Control de Arrobas"
COPYRIGHT = "© Derechos Reservados. Control de Arrobas."
