import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smpc.shamir import secret_share, aggregate_shares, _lagrange_interpolate_at_zero, PRIME


def test_shares_reconstruct_single_value():
    shares = secret_share(42, num_parties=3)
    assert _lagrange_interpolate_at_zero(shares) == 42


def test_shares_are_not_raw_value():
    shares = secret_share(42, num_parties=3)
    for x, y in shares:
        assert y != 42


def test_sum_across_hospitals_correct():
    hospital_values = {"H1": 120, "H2": 95, "H3": 60}
    all_shares = {h: secret_share(v, num_parties=3) for h, v in hospital_values.items()}

    combined = {}
    for position in range(3):
        x = all_shares["H1"][position][0]
        summed_y = sum(all_shares[h][position][1] for h in hospital_values) % PRIME
        combined[f"party_{position+1}"] = (x, summed_y)

    assert aggregate_shares(combined) == sum(hospital_values.values())


def test_zero_value():
    shares = secret_share(0, num_parties=3)
    assert _lagrange_interpolate_at_zero(shares) == 0


def test_different_num_parties():
    shares = secret_share(100, num_parties=5)
    assert len(shares) == 5
    assert _lagrange_interpolate_at_zero(shares) == 100