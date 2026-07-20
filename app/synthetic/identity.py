"""Synthetic identity generation backed by Faker.

These identities are entirely fake. They exist to exercise ingestion, dedup and
validation paths in downstream systems during a controlled resilience test.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from faker import Faker


@dataclass(frozen=True)
class SyntheticIdentity:
    """A fabricated person used to populate a fraud scenario."""

    external_id: str
    name: str
    ssn: str
    email: str
    street: str
    city: str
    postcode: str
    country: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


class IdentityFactory:
    """Produces :class:`SyntheticIdentity` values, optionally deterministically."""

    def __init__(self, seed: int | None = None) -> None:
        self._faker = Faker()
        if seed is not None and seed >= 0:
            self._faker.seed_instance(seed)

    def make(self) -> SyntheticIdentity:
        f = self._faker
        return SyntheticIdentity(
            external_id=f.uuid4(),
            name=f.name(),
            ssn=f.ssn(),
            email=f.free_email(),
            street=f.street_address(),
            city=f.city(),
            postcode=f.postcode(),
            country=f.current_country_code(),
        )
