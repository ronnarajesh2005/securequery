import pyreadstat

FILE_PATH = r"D:\securequery\IAPR7ESV\IAPR7EFL.SAV"

cols = ['HV104', 'HV105', 'SHB18S', 'SHB18D', 'SHB25S', 'SHB25D',
        'SHB29S', 'SHB29D', 'SHB53', 'SHB55', 'SHB56', 'SHB57', 'SHB74']

print("Loading data...")
df, meta = pyreadstat.read_sav(FILE_PATH, usecols=cols)
print(f"Loaded {len(df)} rows\n")

# --- Step 1: restrict to adults (NFHS tests ages 15+) ---
adults = df[df['HV105'] >= 15].copy()
print(f"Adults (15+): {len(adults)}")

# --- Step 2: Hypertension ---
# Average the 3 systolic and 3 diastolic readings per person
bp_cols_sys = ['SHB18S', 'SHB25S', 'SHB29S']
bp_cols_dia = ['SHB18D', 'SHB25D', 'SHB29D']

bp = adults.dropna(subset=bp_cols_sys + bp_cols_dia).copy()
bp['avg_systolic'] = bp[bp_cols_sys].mean(axis=1)
bp['avg_diastolic'] = bp[bp_cols_dia].mean(axis=1)

# Standard hypertension cutoff: systolic >=140 OR diastolic >=90
bp['hypertensive'] = (bp['avg_systolic'] >= 140) | (bp['avg_diastolic'] >= 90)

htn_rate = bp['hypertensive'].mean() * 100
print(f"\n--- Hypertension ---")
print(f"Valid BP readings: {len(bp)}")
print(f"Hypertension prevalence: {htn_rate:.2f}%")

# --- Step 3: Diabetes ---
# SHB56 = told high blood glucose by doctor on 2+ occasions (0=No, 1=Yes)
diabetes_valid = adults.dropna(subset=['SHB56'])
diabetes_valid = diabetes_valid[diabetes_valid['SHB56'].isin([0, 1])]

diabetes_rate = (diabetes_valid['SHB56'] == 1).mean() * 100
print(f"\n--- Diabetes ---")
print(f"Valid diabetes-flag responses: {len(diabetes_valid)}")
print(f"Diabetes prevalence (diagnosed): {diabetes_rate:.2f}%")

# --- Step 4: breakdown by sex, as a sanity check ---
print(f"\n--- Sanity check: by sex ---")
for sex_code, sex_name in [(1, 'Male'), (2, 'Female')]:
    sub_bp = bp[bp['HV104'] == sex_code]
    sub_db = diabetes_valid[diabetes_valid['HV104'] == sex_code]
    print(f"{sex_name}: HTN={sub_bp['hypertensive'].mean()*100:.1f}%  "
          f"Diabetes={(sub_db['SHB56']==1).mean()*100:.1f}%")