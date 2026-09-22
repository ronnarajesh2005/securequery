import sys
sys.path.insert(0, r"D:\securequery\backend")

from app.core.hospital_db import run_sql_on_hospital

sql = "SELECT SUM(EXTRACT(YEAR FROM AGE(T2.date_of_birth))) AS total_sum, COUNT(DISTINCT T2.patient_id) AS total_count FROM conditions AS T1 INNER JOIN patients AS T2 ON T1.patient_id = T2.patient_id WHERE LOWER(T1.condition_desc) LIKE '%hypertension%'"

for hid in ["hospital_a", "hospital_b", "hospital_c"]:
    result = run_sql_on_hospital(hid, sql)
    print(hid, "->", result)