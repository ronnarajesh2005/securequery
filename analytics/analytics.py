import matplotlib
matplotlib.use("Agg")  # non-interactive backend, so it doesn't try to open a GUI window
import matplotlib.pyplot as plt


def build_analytics(results: list) -> dict:
    """
    results: post-risk-check DISCLOSED data only, e.g.
      [{"hospital": "H1", "year": 2023, "disease": "Diabetes", "value": 120}, ...]
    Returns:
      {
        "stats": {...},
        "tables": [...],
        "charts": [...]
      }
    """
    # Filter out any masked/non-numeric entries defensively
    numeric_results = [r for r in results if isinstance(r.get("value"), (int, float))]
    values = [r["value"] for r in numeric_results]

    # --- Descriptive stats ---
    stats = {
        "count": len(values),
        "avg": round(sum(values) / len(values), 2) if values else 0,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }

    # --- Cross-hospital comparison table ---
    hospitals = sorted(set(r["hospital"] for r in numeric_results if "hospital" in r))
    hospital_totals = {
        h: sum(r["value"] for r in numeric_results if r.get("hospital") == h)
        for h in hospitals
    }
    cross_hospital_table = {
        "title": "Cross-hospital comparison",
        "data": [{"hospital": h, "total": total} for h, total in hospital_totals.items()]
    }

    # --- Disease distribution table ---
    diseases = sorted(set(r["disease"] for r in numeric_results if "disease" in r))
    disease_totals = {
        d: sum(r["value"] for r in numeric_results if r.get("disease") == d)
        for d in diseases
    }
    disease_table = {
        "title": "Disease distribution",
        "data": [{"disease": d, "total": total} for d, total in disease_totals.items()]
    }

    # --- Year-over-year trend ---
    years = sorted(set(r["year"] for r in numeric_results if "year" in r))
    yoy_totals = {
        y: sum(r["value"] for r in numeric_results if r.get("year") == y)
        for y in years
    }
    yoy_table = {
        "title": "Year-over-year trend",
        "data": [{"year": y, "total": total} for y, total in yoy_totals.items()]
    }

    # --- Top-N ranking (top 3 by value) ---
    top_n = sorted(numeric_results, key=lambda r: r["value"], reverse=True)[:3]
    top_n_table = {
        "title": "Top-3 rankings",
        "data": [{"group_key": r.get("group_key", f"{r.get('hospital')}-{r.get('disease')}"),
                   "value": r["value"]} for r in top_n]
    }

    # --- Percentage breakdown (by hospital) ---
    total_all = sum(values) if values else 1  # avoid div by zero
    pct_breakdown = {
        "title": "Percentage breakdown by hospital",
        "data": [{"hospital": h, "percent": round((total / total_all) * 100, 1)}
                 for h, total in hospital_totals.items()]
    }

    tables = [cross_hospital_table, disease_table, yoy_table, top_n_table, pct_breakdown]

    # --- Charts ---
    charts = []

    if hospital_totals:
        fig1, ax1 = plt.subplots()
        ax1.bar(list(hospital_totals.keys()), list(hospital_totals.values()))
        ax1.set_title("Cross-hospital comparison")
        ax1.set_ylabel("Total")
        charts.append({"type": "bar", "title": "Cross-hospital comparison", "figure": fig1})

    if disease_totals:
        fig2, ax2 = plt.subplots()
        ax2.pie(list(disease_totals.values()), labels=list(disease_totals.keys()), autopct="%1.1f%%")
        ax2.set_title("Disease distribution")
        charts.append({"type": "pie", "title": "Disease distribution", "figure": fig2})

    if yoy_totals:
        fig3, ax3 = plt.subplots()
        ax3.plot(list(yoy_totals.keys()), list(yoy_totals.values()), marker="o")
        ax3.set_title("Year-over-year trend")
        ax3.set_xlabel("Year")
        ax3.set_ylabel("Total")
        charts.append({"type": "line", "title": "Year-over-year trend", "figure": fig3})

    return {
        "stats": stats,
        "tables": tables,
        "charts": charts
    }


if __name__ == "__main__":
    mock_results = [
        {"group_key": "H1-2023-Diabetes", "hospital": "H1", "year": 2023, "disease": "Diabetes", "value": 120},
        {"group_key": "H1-2024-Diabetes", "hospital": "H1", "year": 2024, "disease": "Diabetes", "value": 140},
        {"group_key": "H2-2023-Diabetes", "hospital": "H2", "year": 2023, "disease": "Diabetes", "value": 95},
        {"group_key": "H2-2023-Hypertension", "hospital": "H2", "year": 2023, "disease": "Hypertension", "value": 60},
        {"group_key": "H3-2023-Diabetes", "hospital": "H3", "year": 2023, "disease": "Diabetes", "value": 80},
    ]
    output = build_analytics(mock_results)
    print("Stats:", output["stats"])
    print("\nTables:")
    for t in output["tables"]:
        print(f"  {t['title']}: {t['data']}")
    print(f"\nGenerated {len(output['charts'])} charts:", [c["title"] for c in output["charts"]])

    # Save charts to disk so you can visually confirm them
    for c in output["charts"]:
        c["figure"].savefig(f"analytics/{c['title'].replace(' ', '_')}.png")
    print("\nCharts saved as PNG files in the analytics/ folder.")