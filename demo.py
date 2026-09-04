"""
End-to-end demo: SecureQuery risk classification + SMPC + analytics.
Simulates 3 hospitals each holding local disease counts, running through
the full pipeline: risk check -> secure aggregation -> analytics.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.risk_pipeline import classify_risk, process_multivalue_result
from smpc.shamir import secret_share, aggregate_shares, PRIME
from analytics.analytics import build_analytics


def demo_single_hospital():
    print("=" * 60)
    print("DEMO 1: Single-hospital query (SMPC skipped)")
    print("=" * 60)
    features = {"result_count": 45, "distinct_sensitive_values": 5, "is_single_hospital": 1}
    result = classify_risk(features)
    print(f"Query: 'Diabetes patients in Hospital H1'")
    print(f"Risk check: {result}")
    if result["disclose"]:
        print("-> Single hospital, disclose flag True: returning H1's own result directly (no SMPC needed).")
    print()


def demo_multivalue_breakdown():
    print("=" * 60)
    print("DEMO 2: Multi-value breakdown (hospital-wise disease counts)")
    print("=" * 60)
    values = [
        {"group_key": "H1-Diabetes", "raw_value": 120, "features": {"result_count": 120, "distinct_sensitive_values": 4}},
        {"group_key": "H2-Diabetes", "raw_value": 95, "features": {"result_count": 95, "distinct_sensitive_values": 4}},
        {"group_key": "H3-RareDisease", "raw_value": 2, "features": {"result_count": 2, "distinct_sensitive_values": 1}},
    ]
    processed = process_multivalue_result(values)
    for item in processed:
        status = "DISCLOSED" if item["disclosed"] else "MASKED"
        print(f"  {item['group_key']}: {item['value']}  [{status}]")
    print()
    return processed


def demo_smpc_aggregation():
    print("=" * 60)
    print("DEMO 3: Secure aggregation across 3 hospitals (SMPC)")
    print("=" * 60)
    hospital_values = {"H1": 120, "H2": 95, "H3": 60}
    print(f"Each hospital's LOCAL value (never shared directly): {hospital_values}")

    all_shares = {h: secret_share(v, num_parties=3) for h, v in hospital_values.items()}
    print("Each hospital splits its value into shares and distributes one share to each party.")
    print("No hospital ever sees another hospital's raw value.\n")

    combined = {}
    for position in range(3):
        x = all_shares["H1"][position][0]
        summed_y = sum(all_shares[h][position][1] for h in hospital_values) % PRIME
        combined[f"party_{position+1}"] = (x, summed_y)

    total = aggregate_shares(combined)
    print(f"Securely reconstructed total: {total}")
    print(f"(True sum for comparison: {sum(hospital_values.values())})")
    print()
    return total


def demo_analytics(processed_values, total):
    print("=" * 60)
    print("DEMO 4: Analytics on final disclosed results")
    print("=" * 60)
    results = [
        {"hospital": "H1", "year": 2023, "disease": "Diabetes", "value": 120},
        {"hospital": "H2", "year": 2023, "disease": "Diabetes", "value": 95},
        {"hospital": "H3", "year": 2023, "disease": "Diabetes", "value": 60},
    ]
    output = build_analytics(results)
    print("Stats:", output["stats"])
    for t in output["tables"]:
        print(f"  {t['title']}: {t['data']}")
    print(f"Charts generated: {[c['title'] for c in output['charts']]}")
    print()


if __name__ == "__main__":
    demo_single_hospital()
    processed = demo_multivalue_breakdown()
    total = demo_smpc_aggregation()
    demo_analytics(processed, total)
    print("=" * 60)
    print("Demo complete. All 4 pipeline stages executed successfully.")
    print("=" * 60)