import os
import psycopg2
from rl.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

def run_migration():
    sql_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(sql_path, 'r') as f:
        sql = f.read()
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration() 