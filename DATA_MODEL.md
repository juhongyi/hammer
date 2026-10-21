# PostgreSQL persistence contracts

## Ownership and startup

`presentation-api` connects only to `presentation-db`; `ontology-api` connects
only to `ontology-db`. Each PostgreSQL 18 service has its own credentials and
volume mounted at `/var/lib/postgresql`. There are no cross-database foreign
keys or direct database reads between products.

Copy `.env.example` to `.env`, replace the example passwords, and run
`docker compose up --build --wait`. Each API runs its own
`uv run --locked alembic upgrade head` before starting Uvicorn. The same
PostgreSQL/Psycopg URL construction and migrations apply in deployment; provide
`PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, and `PGPASSWORD` there.
The former shared development volume is not reused by the new services.

All commands below run inside Compose:

```sh
docker compose exec presentation-api uv run --locked alembic current
docker compose exec ontology-api uv run --locked alembic current
docker compose exec presentation-api uv run --locked pytest
docker compose exec ontology-api uv run --locked pytest
```

`lefthook run pre-push --force --no-auto-install` starts the services, checks
migration/model consistency, and runs the complete backend/web verification.
For example configuration without `.env`, export
`COMPOSE_ENV_FILES=.env.example`. Occupied host ports can be overridden using
the four `*_PORT` variables in that file.

## Presentation database

| Table | Fields and relationships |
|---|---|
| `presentation` | UUID PK, immutable input text, outline JSONB, status, confirmation timestamp, failure reason |
| `generation` | UUID PK, presentation FK, full design snapshot JSONB, ordered generated pages JSONB, timestamp |
| `record` | UUID PK, presentation FK, stage, kind, optional model ID/page position, attempt, payload JSONB, timestamp |

The outline is one atomic aggregate, not independently editable table rows.
Its validated Pydantic contracts are `Outline`, `Chapter`, `Page`, and `Content`
in `presentation/api/app/schemas.py`:

- `cover_title` represents the single first slide, outside all chapters.
- `pages` contains 5–29 body pages, in slide order, giving 6–30 total slides.
  Each page has a stable UUID, title, key message, and up to six title/description
  content items.
- Each chapter has a stable UUID, title, and one or more ordered `page_ids`.
  Flattening the chapters' page IDs must exactly equal the ordered page IDs.
  This rejects duplicates, gaps, overlaps, and noncontiguous groups. A chapter
  title is not a slide.

`PresentationCreate` accepts the request and an already generated/validated
outline. `PresentationRepository` provides create/get, text-only outline edits,
confirmation, failure storage, result storage/query, and audit append/query.
It is the persistence interface for the later generation API; it does not
invoke models or expose new generation/editing HTTP endpoints.

Outline writes are revalidated at the repository boundary. Editing cannot
change page IDs/order or chapter IDs/membership. Mutations lock the presentation
row for the entire transaction, preventing concurrent edit/confirm/result races.
States are `editing → confirmed → completed`, or `confirmed → failed`.
A validated result may complete a failed presentation without changing its
confirmed outline. There is no background job table or queue.

DB checks enforce state values, confirmation/failure consistency and page-count
bounds. A trigger protects the confirmed outline, confirmation timestamp, and
input request even against direct SQL updates. Completed status cannot regress.
Cross-page structure constraints are enforced by Pydantic and repository
transactions, not by JSONB field-level foreign keys.

## Ontology database

| Table | Fields and relationships |
|---|---|
| `expression_type` | String PK, purpose, suitable/unsuitable conditions, enabled |
| `layout` | String PK, purpose, required content, min/max item count, enabled |
| `layout_support` | Composite PK and FKs `(layout_id, expression_type_id)` |
| `slot` | Composite PK `(layout_id, id)`, role, text/items shape, required, position, repetition min/max, max length |

`OntologyDefinition`, `ExpressionType`, `Layout`, and `Slot` in
`ontology/api/app/schemas.py` define the wire contract. Slot positions are unique
and contiguous within a layout; slot IDs are scoped to layouts. Item bounds,
positive capacity, support uniqueness, and foreign keys are checked in the DB
where possible and at the contract boundary. `required_content` describes
required content/structure; slot counts and lengths provide exact capacity
constraints.

`OntologyRepository.save` atomically upserts supplied definitions, replaces
their slots/supports, and retains omitted definitions. `get` reads a consistent
repeatable-read snapshot. These are persistence operations, not public design
registration or operator review APIs. Initial six-layout seed data and operator
review/activation workflows belong to #11 (with renderer capacities from #10).

## Snapshot and result contracts

`OntologyDefinition.model_dump(mode="json")` is the version 1 transfer document:

```json
{
  "schema_version": 1,
  "expression_types": [
    {"id": "message", "purpose": "핵심 전달", "suitable": "요약", "unsuitable": "비교", "enabled": true}
  ],
  "layouts": [
    {
      "id": "message", "purpose": "핵심 메시지", "expression_type_ids": ["message"],
      "required_content": [], "min_items": 0, "max_items": 6, "enabled": true,
      "slots": [{"id": "title", "role": "제목", "data_type": "text", "required": true,
                 "position": 0, "min_items": 0, "max_items": 1, "max_length": 100}]
    }
  ]
}
```

The presentation-side `DesignSnapshot` retains the complete document, including
all definition fields, without looking up mutable ontology rows. It validates
the version and unique definition IDs; ontology field validation is owned by
`OntologyDefinition`. Keep the definitions considered during classification and
candidate selection, not just the final selected layout. The future HTTP client
must validate the ontology contract before passing it to persistence.

`GenerationCreate` contains that snapshot and ordered `GeneratedPage` values.
Position 0 is the cover; positions 1…N correspond to the confirmed body-page
order. Each value includes expression type/layout IDs, slot text or content
items, and semantic/structure/layout check outcomes. Selected IDs must exist in
the snapshot and the layout must support the selected type. A complete result
must match the confirmed slide count and every page must pass all checks.
Completion and result insertion happen in the same transaction.

Generation rows and audit records are append-only, enforced by database
triggers. No update/delete repository operations are exposed. Updating or
disabling ontology definitions therefore cannot change existing snapshots or
rendered content. Failed generation stores a reason while retaining the
confirmed outline and audit history; it creates no completed generation row.

`RecordCreate` records `candidates`, `decision`, `semantic_review`, or `validation`
for an explicit stage, optional model ID and page position, and attempt 1 or 2.
Its JSON payload carries stage-specific candidate definitions/IDs, model input,
judgment, selection, pass/fail reasons, or validation errors. Records can be
stored before a result exists, so failed attempts remain inspectable. Candidate
records should include the considered definitions when no completed result
exists. Both result and record read contracts include IDs and timestamps and
are queried by presentation ID.

HTTP generation orchestration, model calls, service-to-service retrieval,
ontology management endpoints, and rendering are implemented by #10–#12 using
these contracts.
