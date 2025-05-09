import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from dotenv import load_dotenv

load_dotenv('app/conf/.env')

Base = declarative_base()

class Database:
    def __init__(self):
        self.db_user = os.getenv("NUECS_MYSQL_USER")
        self.db_pwd = os.getenv("NUECS_MYSQL_PASSWORD")
        self.db_host = os.getenv("NUECS_MYSQL_HOST")
        self.db_port = os.getenv("NUECS_MYSQL_PORT")
        self.db_name = os.getenv("NUECS_MYSQL_NAME")
        self._engine = None
        self._SessionLocal = None

    def connect(self):
        database_url = (
            # f"mysql+pymysql://{self.db_user}:{self.db_pwd}@{self.db_host}:{self.db_port}/{self.db_name}"
            f"mssql+pyodbc://{self.db_user}:{self.db_pwd}@{self.db_host},{self.db_port}/{self.db_name}?driver=ODBC+Driver+17+for+SQL+Server"
        )
        self._engine = create_engine(database_url, pool_pre_ping=True)
        self._SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self._engine)
        return self

    def get_session(self) -> Session:
        if not self._SessionLocal:
            raise RuntimeError("Database not connected. Call `connect()` first.")
        return self._SessionLocal()

    def create_all_tables(self):
        if not self._engine:
            raise RuntimeError("Database not connected. Call `connect()` first.")
        Base.metadata.create_all(bind=self._engine)

def get_db():
    from main import app
    db = app.state.db.get_session()
    try:
        yield db
    finally:
        db.close()