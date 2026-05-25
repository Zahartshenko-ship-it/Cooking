from sqlalchemy import create_engine, text

def get_engine():
    DB_USER = 'postgres'
    DB_PASSWORD = 'JohnnyCage29'
    DB_HOST = '159.194.211.35'
    DB_PORT = '5432'
    DB_NAME = 'mydb'
    return create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")