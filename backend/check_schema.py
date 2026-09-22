import psycopg2

conn = psycopg2.connect(host="localhost", port=5433, database="hospital_a", user="hospital_a_admin", password="HospitalA_2026!")
cur = conn.cursor()

try:
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'conditions'")
    print("COLUMNS:", cur.fetchall())
except Exception as e:
    print("COLUMN QUERY ERROR:", e)
    conn.rollback()

try:
    cur.execute("SELECT COUNT(*) FROM conditions")
    print("ROW COUNT:", cur.fetchone())
except Exception as e:
    print("COUNT ERROR:", e)
    conn.rollback()

cur.close()
conn.close()