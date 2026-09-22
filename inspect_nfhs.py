import pyreadstat

FILE_PATH = r"D:\securequery\IAPR7ESV\IAPR7EFL.SAV"

usecols = [
    "HV104",
    "HV105",

    # Blood pressure
    "SHB18S",
    "SHB18D",
    "SHB25S",
    "SHB25D",
    "SHB29S",
    "SHB29D",

    # Blood glucose / diabetes
    "SHB55",
    "SHB56",
    "SHB57",
    "SHB53",
    "SHB74"
]

print("Loading required NFHS-5 variables...")
print("This may take a while because the source file is 2.36 GB.")

df, meta = pyreadstat.read_sav(
    FILE_PATH,
    usecols=usecols
)

print("\nLoaded successfully!")
print("Rows:", len(df))
print("Columns:", len(df.columns))

print("\nVariable names:")
print(df.columns.tolist())

print("\nFirst 5 rows:")
print(df.head())