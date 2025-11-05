import os
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

# Create engine and session
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Definición de Base para modelos SQLAlchemy
from sqlalchemy.orm import declarative_base
Base = declarative_base()