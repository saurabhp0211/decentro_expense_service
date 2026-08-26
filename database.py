from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLALCHEMY_DATABASE_URL = "sqlite:///./expenses.db"
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:root@localhost:5432/decentro_expenses"

engine=create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal=sessionmaker(autocommit=False, autoflush=False, bind=engine)

# @event.listens_for(Engine,"connect")
# def set_sqlite_pragma(dbapi_connection, connection_record):
#     cursor=dbapi_connection.cursor()
#     cursor.execute("PRAGMA foreign_keys=ON")
#     cursor.close()

Base=declarative_base()

def get_db():
    db=SessionLocal()
    try:
        yield db
    finally: 
        db.close()