from agritwin_core.device_auth import generate_api_key, hash_api_key, verify_api_key


def test_generated_keys_are_unique_and_high_entropy():
    keys = {generate_api_key() for _ in range(100)}
    assert len(keys) == 100
    assert all(len(k) >= 32 for k in keys)


def test_verify_api_key_accepts_correct_key():
    raw = generate_api_key()
    assert verify_api_key(raw, hash_api_key(raw)) is True


def test_verify_api_key_rejects_wrong_key():
    raw = generate_api_key()
    other = generate_api_key()
    assert verify_api_key(other, hash_api_key(raw)) is False


def test_hash_is_deterministic():
    raw = generate_api_key()
    assert hash_api_key(raw) == hash_api_key(raw)
