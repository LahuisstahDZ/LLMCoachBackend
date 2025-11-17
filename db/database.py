from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

from urllib.parse import quote_plus


def _strip_quotes(value: str | None) -> str | None:
	if value is None:
		return None
	# remove surrounding whitespace and any single/double quotes
	return value.strip().strip('"').strip("'")


# Prefer an explicit DATABASE_URL if provided (cleaned of surrounding quotes)
db_user = _strip_quotes(os.getenv('DB_USER', 'llmcoach_db_user'))
db_password = _strip_quotes(os.getenv('DB_PASSWORD', '')) or ''
db_host = _strip_quotes(os.getenv('DB_HOST', 'localhost'))
db_port = _strip_quotes(os.getenv('DB_PORT', '5432'))
db_name = _strip_quotes(os.getenv('DB_NAME', 'llmcoach_db'))

password_esc = quote_plus(db_password)
DATABASE_URL = f"postgresql://{db_user}:{password_esc}@{db_host}:{db_port}/{db_name}"


# create engine (future flag for modern SQLAlchemy behavior)
engine = create_engine(DATABASE_URL, future=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
