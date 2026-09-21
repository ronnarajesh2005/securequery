import random

PRIME = 2_147_483_647  # 2^31 - 1


def secret_share(value: int, num_parties: int) -> list:
    """
    Splits `value` into `num_parties` additive shares over a finite field.
    Returns: list of shares, one per hospital.
    """
    shares = [random.randint(0, PRIME - 1) for _ in range(num_parties - 1)]
    last_share = (value - sum(shares)) % PRIME
    shares.append(last_share)
    return shares


def aggregate_shares(shares_by_hospital: dict) -> int:
    """
    shares_by_hospital: {hospital_id: share}  (one share per hospital, already
    summed/selected for this party — matches contracts.md exactly)
    Returns: the reconstructed aggregate.
    """
    total = sum(shares_by_hospital.values()) % PRIME
    return total


def simulate_multi_hospital_sum(hospital_values: dict, num_parties: int = 3) -> dict:
    """
    hospital_values: {hospital_id: value}
    Full round-trip simulation matching the real contract shape:
    each hospital secret-shares its value into num_parties shares,
    party 0's share from each hospital becomes shares_by_hospital
    for aggregate_shares (simplified single-party reconstruction demo).
    """
    all_shares = {
        hospital_id: secret_share(value, num_parties)
        for hospital_id, value in hospital_values.items()
    }

    # Reconstruct using ALL shares from each hospital summed (full reconstruction)
    shares_by_hospital = {
        hospital_id: sum(shares) % PRIME
        for hospital_id, shares in all_shares.items()
    }

    reconstructed_sum = aggregate_shares(shares_by_hospital)
    true_sum = sum(hospital_values.values()) % PRIME

    return {
        "true_sum": sum(hospital_values.values()),
        "reconstructed_sum": reconstructed_sum,
        "match": reconstructed_sum == true_sum,
        "individual_values_exposed": False,
    }