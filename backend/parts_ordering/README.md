# Parts Ordering

The requirement-to-goods-receipt workflow behind the Parts branch of
[The Ground](../../src/ground/data/graph.ts). The graph explains the process;
this is the process, runnable — raise a requirement, check availability,
place an order, allocate stock, ship, receive. The seven stages are that
graph's own seven node names (`Parts Requirement`, `Part Identification`,
`Parts Availability`, `Parts Ordering`, `Inventory`, `Shipment`,
`Goods Receipt`), so the working tool and the diagram that explains it never
disagree about what to call a step.

FastAPI + SQLAlchemy, SQLite by default, Postgres-ready — see `.env.example`.

## Run it

```bash
cd backend/parts_ordering
python -m venv .venv
.venv/Scripts/activate        # .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt

cp .env.example .env          # optional — the defaults work with no .env at all

alembic upgrade head          # creates the schema
uvicorn app.main:app --reload --port 8000
```

The API is then at `http://localhost:8000`, interactive docs at
`http://localhost:8000/docs`. The ten parts and their starting stock seed
themselves on first run — see `app/seed.py` for exactly what and why.

## Test it

```bash
pytest
```

Every test runs against its own in-memory database (see `tests/conftest.py`)
— nothing touches the real `parts_ordering.db` file, and no test can see
another's data.

## The workflow

```
POST /api/requirements                                 → requirement_raised, identified
POST /api/requirements/{id}/check-availability          → availability_checked
POST /api/requirements/{id}/order       {supplier?}     → ordered
POST /api/requirements/{id}/allocate                    → inventory_allocated
POST /api/requirements/{id}/ship        {carrier?}      → shipped
POST /api/requirements/{id}/receive                     → received
```

Each action only succeeds from the stage before it — skip one and the API
answers `409 Conflict` naming the stage it actually needs, not a generic
failure. `allocate` also fails with `409` if there is not enough physically
on hand, rather than letting stock go negative. `GET /api/requirements/{id}`
returns the full timeline (`events`) alongside the current stage, so a
detail view can render the whole history, not just where things stand now.

## Schema changes

The schema is owned by Alembic, not by the app starting up. Change a model
in `app/models.py`, then:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

Review the generated migration before committing it — autogenerate is a
first draft, not a guarantee.

## Why FastAPI + SQLite-that-becomes-Postgres

This backend exists because the parts-ordering workflow needed to be a real,
persistent, server-enforced process rather than state living only in a
browser tab — that was an explicit decision, not the default for this
project (the rest of the site is a static Vite build with no server at all).
SQLite keeps it runnable with zero infrastructure; every model and every
migration is written against plain SQLAlchemy, so pointing `DATABASE_URL` at
Postgres is a one-line change whenever there is a Postgres to point at, not
a rewrite.
