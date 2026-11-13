import os
import pymysql

PASSWORD = os.getenv("SMARTFLOW_DB_PASSWORD", "nilesh@123")   # your MySQL root password

here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "schema.sql"), encoding="utf-8") as f:
    statements = [s.strip() for s in f.read().split(";") if s.strip()]

conn = pymysql.connect(host="localhost", user="root", password=PASSWORD)
with conn.cursor() as cur:
    for s in statements:
        cur.execute(s)
conn.commit()
conn.close()
print("Done: database 'smartflow' and all tables created")