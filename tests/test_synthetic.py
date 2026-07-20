from app.synthetic.identity import IdentityFactory, SyntheticIdentity


def test_identity_has_all_fields():
    identity = IdentityFactory().make()
    assert isinstance(identity, SyntheticIdentity)
    data = identity.as_dict()
    for field in ("external_id", "name", "ssn", "email", "street", "city", "postcode", "country"):
        assert data[field], f"{field} should be populated"


def test_seed_is_deterministic():
    a = IdentityFactory(seed=42).make()
    b = IdentityFactory(seed=42).make()
    assert a == b


def test_different_seeds_differ():
    a = IdentityFactory(seed=1).make()
    b = IdentityFactory(seed=2).make()
    assert a != b
