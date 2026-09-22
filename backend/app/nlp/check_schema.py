from app.core.hospital_db import HOSPITAL_DBS
import psycopg2

conn = psycopg2.connect(**HOSPITAL_DBS['hospital_a'])
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
print(cur.fetchall())
cur.close()
conn.close()