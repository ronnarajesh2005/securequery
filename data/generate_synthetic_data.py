import numpy as np
import pandas as pd

def generate_dataset(n_samples: int = 5000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    result_count = rng.integers(0, 500, size=n_samples)
    distinct_sensitive_values = rng.integers(1, 10, size=n_samples)
    query_granularity = rng.integers(1, 5, size=n_samples)
    is_single_hospital = rng.integers(0, 2, size=n_samples)

    k_threshold = 5
    l_threshold = 2

    label = (
        (result_count >= k_threshold) &
        (distinct_sensitive_values >= l_threshold)
    ).astype(int)

    flip_mask = rng.random(n_samples) < 0.03
    label = np.where(flip_mask, 1 - label, label)

    df = pd.DataFrame({
        "result_count": result_count,
        "distinct_sensitive_values": distinct_sensitive_values,
        "query_granularity": query_granularity,
        "is_single_hospital": is_single_hospital,
        "label": label
    })
    return df

if __name__ == "__main__":
    df = generate_dataset()
    df.to_csv("data/synthetic_risk_data.csv", index=False)
    print(df.head())
    print(f"\nGenerated {len(df)} rows. Label distribution:\n{df['label'].value_counts()}")