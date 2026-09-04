import random

# A large prime number, bigger than any value we expect to secret-share.
# All arithmetic happens modulo this prime (finite field).
PRIME = 2**61 - 1


def _eval_polynomial(coeffs, x):
    """Evaluate polynomial (coeffs[0] + coeffs[1]*x + coeffs[2]*x^2 + ...) mod PRIME."""
    result = 0
    for power, coeff in enumerate(coeffs):
        result = (result + coeff * pow(x, power, PRIME)) % PRIME
    return result


def secret_share(value: int, num_parties: int, threshold: int = None) -> list:
    """
    Splits `value` into `num_parties` shares using Shamir's Secret Sharing.
    Any `threshold` shares (default = num_parties) can reconstruct the value;
    fewer than that reveal nothing.
    Returns a list of (x, y) tuples, one per party (hospital).
    """
    if threshold is None:
        threshold = num_parties

    # Random polynomial: value + a1*x + a2*x^2 + ... + a(threshold-1)*x^(threshold-1)
    coeffs = [value % PRIME] + [random.randint(1, PRIME - 1) for _ in range(threshold - 1)]

    shares = []
    for i in range(1, num_parties + 1):
        y = _eval_polynomial(coeffs, i)
        shares.append((i, y))
    return shares


def _lagrange_interpolate_at_zero(points):
    """Reconstructs the secret (the polynomial's value at x=0) from given points."""
    total = 0
    for i, (xi, yi) in enumerate(points):
        num, den = 1, 1
        for j, (xj, _) in enumerate(points):
            if i != j:
                num = (num * (-xj)) % PRIME
                den = (den * (xi - xj)) % PRIME
        total = (total + yi * num * pow(den, PRIME - 2, PRIME)) % PRIME
    return total


def aggregate_shares(shares_by_hospital: dict) -> int:
    """
    shares_by_hospital: {hospital_id: (x, y) share tuple}
    Reconstructs the SUM of all hospitals' original secret values.

    How this works: each hospital secret-shares its own local value.
    We take hospital #k's share at the SAME polynomial position from
    every hospital's separate sharing, sum those y-values together
    (this works because Shamir shares are additively homomorphic),
    then interpolate to recover the total sum — without any hospital
    ever seeing another's raw value.
    """
    points = list(shares_by_hospital.values())
    return _lagrange_interpolate_at_zero(points)


if __name__ == "__main__":
    # --- Test 1: reconstruct a single secret-shared value ---
    shares = secret_share(42, num_parties=3)
    print("Shares:", shares)
    reconstructed = _lagrange_interpolate_at_zero(shares)
    print("Reconstructed:", reconstructed)

    # --- Test 2: secure summation across 3 hospitals ---
    # Each hospital has its own local count (e.g. diabetes patients in 2023)
    hospital_values = {"H1": 120, "H2": 95, "H3": 60}
    print("\nHospital local values (never shown to each other in real use):", hospital_values)

    # Each hospital independently secret-shares its own value into 3 shares
    # (one share per hospital, including itself)
    all_shares = {
        hospital: secret_share(value, num_parties=3)
        for hospital, value in hospital_values.items()
    }

    # Now simulate: each hospital sums the shares IT RECEIVED (position-wise)
    # Hospital i collects share[i] from every other hospital's split
    combined_shares_by_position = {}
    for position in range(3):  # 0, 1, 2 -> corresponds to share index for H1, H2, H3
        x = all_shares["H1"][position][0]  # x-coordinate is the same across hospitals at this position
        summed_y = sum(all_shares[h][position][1] for h in hospital_values) % PRIME
        combined_shares_by_position[f"party_{position+1}"] = (x, summed_y)

    total = aggregate_shares(combined_shares_by_position)
    expected = sum(hospital_values.values())
    print(f"\nReconstructed total (via SMPC): {total}")
    print(f"Expected total (plain sum):     {expected}")
    print("Match!" if total == expected else "MISMATCH — bug!")