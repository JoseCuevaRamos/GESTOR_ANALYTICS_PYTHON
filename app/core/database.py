import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_DATABASE = os.getenv("DB_DATABASE", "testdb")
DB_USERNAME = os.getenv("DB_USERNAME", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_PORT = os.getenv("DB_PORT", "3306")

DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Definición de Base para modelos SQLAlchemy
from sqlalchemy.orm import declarative_base
Base = declarative_base()