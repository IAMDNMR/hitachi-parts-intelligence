"""
Every test gets its own in-memory database, seeded fresh — no test can see
another's data, and none of them touch the real `parts_ordering.db` file a
developer might have open. `get_db` is the only thing overridden; the routes
and the workflow service run completely unmodified, so a passing test means
the actual request path works, not a mock of it.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.seed import seed


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    seed(db)
    db.close()

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


# The seeded machines these tests build on. A requirement now names a machine
# rather than a string, so the fixtures that used to pass "ZX350-4521" or "X"
# pass an id — and the model matters, because fitment is validated against it.
#
#   zx350-4521   ZX350LC-7   the serial carried over from the free-text era
#   zx210-0087   ZX210-7     the smallest machine; fewer parts fit it
#   zx490-0031   ZX490LCH-7  in the workshop
A_MACHINE = "zx350-4521"
A_SMALL_MACHINE = "zx210-0087"
