from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# Prefer an explicit DATABASE_URL if provided (cleaned of surrounding quotes)
db_user = os.getenv('DB_USER', 'llmcoach_db_user')
db_password = os.getenv('DB_PASSWORD', '')
db_host = os.getenv('DB_HOST', 'localhost')
db_port = os.getenv('DB_PORT', '5432')
db_name = os.getenv('DB_NAME', 'llmcoach_db')

#DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
DATABASE_URL = os.getenv('DATABASE_URL')

# create engine (future flag for modern SQLAlchemy behavior)
engine = create_engine(DATABASE_URL, future=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
