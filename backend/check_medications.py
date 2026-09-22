from app.core.hospital_db import HOSPITAL_DBS
import psycopg2

conn = psycopg2.connect(**HOSPITAL_DBS['hospital_a'])
cur = conn.cursor()
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'medications'
""")
print("MEDICATIONS COLUMNS:", cur.fetchall())

cur.execute("SELECT COUNT(*) FROM medications")
print("ROW COUNT:", cur.fetchone())

cur.execute("SELECT * FROM medications LIMIT 3")
print("SAMPLE ROWS:", cur.fetchall())

cur.close()
conn.close()