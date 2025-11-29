import os
import base64
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
load_dotenv()

# Support separate analytics (read-only) DB credentials for the Python backend.
# If ANALYTICS_DB_* variables are present they will be used; otherwise fall
# back to the main DB_* variables. This allows the PHP backend to keep using
# its DB credentials while Python uses a reduced-permissions user.
DB_HOST = os.getenv("ANALYTICS_DB_HOST") or os.getenv("DB_HOST", "localhost")
DB_DATABASE = os.getenv("DB_DATABASE", "testdb")
DB_USERNAME = os.getenv("ANALYTICS_DB_USERNAME") or os.getenv("DB_USERNAME", "user")
DB_PASSWORD = os.getenv("ANALYTICS_DB_PASSWORD") or os.getenv("DB_PASSWORD", "password")
DB_PORT = os.getenv("ANALYTICS_DB_PORT") or os.getenv("DB_PORT", "3306")

DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"

# Habilitar SSL/TLS automáticamente si el host contiene 'tidb'.
# Si se proporciona DB_SSL_CA (ruta o contenido del cert), se usará como CA.
connect_args = {}

# SSL/TLS support:
# - If DB_SSL_CA_B64 is provided, decode PEM to a temp file and use it.
# - Else, if DB_SSL_CA is provided, use it directly (path to PEM in container).
# - Else, if host suggests a managed cloud (e.g., contains 'tidb'), enable SSL without CA.
db_ssl_ca_b64 = os.getenv('DB_SSL_CA_B64', '').strip()
db_ssl_ca_path = os.getenv('DB_SSL_CA', '').strip()

temp_ca_path = None
if db_ssl_ca_b64:
	try:
		pem_bytes = base64.b64decode(db_ssl_ca_b64)
		# Write to a secure temporary file. Keep it for the life of the process.
		tmp = tempfile.NamedTemporaryFile(prefix="db_ca_", suffix=".pem", delete=False)
		tmp.write(pem_bytes)
		tmp.flush()
		tmp.close()
		temp_ca_path = tmp.name
		connect_args = {"ssl": {"ca": temp_ca_path}}
	except Exception:
		# If decoding fails, fall back to other mechanisms
		pass
elif db_ssl_ca_path:
	connect_args = {"ssl": {"ca": db_ssl_ca_path}}
elif 'tidb' in (DB_HOST or '').lower():
	# Enable SSL even without CA to force TLS in many cloud providers
	connect_args = {"ssl": {}}

# Create engine and session (pasar connect_args si corresponde)
if connect_args:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Definición de Base para modelos SQLAlchemy
from sqlalchemy.orm import declarative_base
Base = declarative_base()