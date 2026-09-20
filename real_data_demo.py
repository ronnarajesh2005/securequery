import sys
sys.path.insert(0, '.')
from analytics.analytics import build_analytics

results = [
    {'hospital': 'Hospital A', 'year': 2016, 'disease': 'Type 2 Diabetes', 'value': 6},
    {'hospital': 'Hospital A', 'year': 2017, 'disease': 'Type 2 Diabetes', 'value': 5},
    {'hospital': 'Hospital A', 'year': 2018, 'disease': 'Type 2 Diabetes', 'value': 5},
    {'hospital': 'Hospital A', 'year': 2019, 'disease': 'Type 2 Diabetes', 'value': 1},
    {'hospital': 'Hospital A', 'year': 2020, 'disease': 'Type 2 Diabetes', 'value': 3},
    {'hospital': 'Hospital A', 'year': 2021, 'disease': 'Type 2 Diabetes', 'value': 2},
    {'hospital': 'Hospital A', 'year': 2022, 'disease': 'Type 2 Diabetes', 'value': 3},
    {'hospital': 'Hospital A', 'year': 2023, 'disease': 'Type 2 Diabetes', 'value': 5},
    {'hospital': 'Hospital A', 'year': 2024, 'disease': 'Type 2 Diabetes', 'value': 5},
    {'hospital': 'Hospital A', 'year': 2025, 'disease': 'Type 2 Diabetes', 'value': 3},
    {'hospital': 'Hospital A', 'year': 2026, 'disease': 'Type 2 Diabetes', 'value': 3},

    {'hospital': 'Hospital B', 'year': 2016, 'disease': 'Type 2 Diabetes', 'value': 7},
    {'hospital': 'Hospital B', 'year': 2017, 'disease': 'Type 2 Diabetes', 'value': 1},
    {'hospital': 'Hospital B', 'year': 2018, 'disease': 'Type 2 Diabetes', 'value': 2},
    {'hospital': 'Hospital B', 'year': 2019, 'disease': 'Type 2 Diabetes', 'value': 1},
    {'hospital': 'Hospital B', 'year': 2020, 'disease': 'Type 2 Diabetes', 'value': 2},
    {'hospital': 'Hospital B', 'year': 2021, 'disease': 'Type 2 Diabetes', 'value': 3},
    {'hospital': 'Hospital B', 'year': 2022, 'disease': 'Type 2 Diabetes', 'value': 4},
    {'hospital': 'Hospital B', 'year': 2023, 'disease': 'Type 2 Diabetes', 'value': 7},
    {'hospital': 'Hospital B', 'year': 2024, 'disease': 'Type 2 Diabetes', 'value': 2},
    {'hospital': 'Hospital B', 'year': 2025, 'disease': 'Type 2 Diabetes', 'value': 5},
    {'hospital': 'Hospital B', 'year': 2026, 'disease': 'Type 2 Diabetes', 'value': 8},

    {'hospital': 'Hospital C', 'year': 2016, 'disease': 'Type 2 Diabetes', 'value': 5},
    {'hospital': 'Hospital C', 'year': 2017, 'disease': 'Type 2 Diabetes', 'value': 3},
    {'hospital': 'Hospital C', 'year': 2018, 'disease': 'Type 2 Diabetes', 'value': 4},
    {'hospital': 'Hospital C', 'year': 2019, 'disease': 'Type 2 Diabetes', 'value': 5},
    {'hospital': 'Hospital C', 'year': 2020, 'disease': 'Type 2 Diabetes', 'value': 4},
    {'hospital': 'Hospital C', 'year': 2021, 'disease': 'Type 2 Diabetes', 'value': 5},
    {'hospital': 'Hospital C', 'year': 2022, 'disease': 'Type 2 Diabetes', 'value': 7},
    {'hospital': 'Hospital C', 'year': 2023, 'disease': 'Type 2 Diabetes', 'value': 3},
    {'hospital': 'Hospital C', 'year': 2024, 'disease': 'Type 2 Diabetes', 'value': 3},
    {'hospital': 'Hospital C', 'year': 2025, 'disease': 'Type 2 Diabetes', 'value': 5},
]

output = build_analytics(results)
print('Stats:', output['stats'])
for t in output['tables']:
    print(f"  {t['title']}: {t['data']}")
print('Charts generated:', [c['title'] for c in output['charts']])

for c in output['charts']:
    c['figure'].savefig(f"analytics/REAL_{c['title'].replace(' ', '_')}.png")
print('Real-data charts saved with REAL_ prefix in analytics/ folder.')