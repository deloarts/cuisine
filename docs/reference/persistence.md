# persistence

Models, column types, repositories, the unit of work, the settings storage, and public ids with the resolver and the instance id. The concept is in [CONTRIBUTING.md section 3.4](../CONTRIBUTING.md#34-persistence).

- [1 engine and sessions](#1-engine-and-sessions)
- [2 models and column types](#2-models-and-column-types)
- [3 repositories](#3-repositories)
- [4 settings](#4-settings)
- [5 public ids, the resolver and the instance id](#5-public-ids-the-resolver-and-the-instance-id)

## 1 engine and sessions

1. `adapters/outbound/persistence/session.py` is the only place that builds an engine. On Postgres every connection starts with statement, lock and idle-in-transaction timeouts; on SQLite foreign keys are switched on per connection, so `ON DELETE` rules behave like on Postgres.
2. Sessions use `expire_on_commit=False` and `autoflush=False`. A repository flushes after its writes, so database-generated ids are available, and loads what it returns explicitly.
3. One request uses one session (`deps.get_db`), shared by every repository of the request through `Platform`.

## 2 models and column types

1. Every model inherits `Base`, whose metadata carries a naming convention, so constraints have the same names on Postgres and SQLite and migrations can address them.
2. Timestamps are `UtcDateTime`, which stores timezone-aware UTC and reads it back as UTC on SQLite too.
3. Lists and objects are `JsonType` (JSONB on Postgres, JSON elsewhere).
4. Secrets the app must read back are `EncryptedString` ([ADR 0004](../adr/0004-secret-encryption-at-rest.md)). A value no configured key can decrypt loads as `None` and logs an error.
5. Bytes are `LargeBinary` (bytea on Postgres).
6. A new model is exported from `models/__init__.py`, or Alembic's autogenerate does not see it.

## 3 repositories

1. A repository maps rows to entities and back; nothing above it sees a model.
2. Repositories whose entity mirrors the model column by column inherit `_SimpleRepository` (`security_repositories.py`), which copies fields by name. Anything with enums, relations or derived fields maps by hand (`user_repository.py`).
3. A repository loads related ids in one extra query per call, never per row (a user's groups, a group's members).
4. Repositories never commit; the use case does, through the unit of work.

## 4 settings

1. The admin settings are dataclasses, one per section (`domain/entities/settings.py`), stored as one JSON row per section in the `settings` table.
2. Reading merges the stored values over the dataclass defaults and drops keys the dataclass no longer has, so adding or removing a setting needs no migration. Renaming one does: a data migration has to move the value.
3. The mail password is encrypted inside the JSON with the secret box; every other value is stored as is.
4. The `instance` row holds the instance's own id (`instance_id`), which is no admin section: `ISettingsRepository.instance_id` creates it on the first call and returns the stored one ever after, and the startup seed calls it (`bootstrap/seed.py`, `ensure_instance_id`). Two first calls at once agree, since the loser of the insert reads the winner's id.

## 5 public ids, the resolver and the instance id

1. A random `uuid4` is the public id of every row people, agents or imports create. A row the reference seed inserts gets `uuid5(SEED_NAMESPACE, "<kind>:<seed key>")` instead (`cookbook/domain/services/seed_ids.py`, kinds `unit`, `category`, `tag`, `family`, `ingredient`, `equipment`), so a base catalogue entry has the same public id on every instance. The namespace never changes.
2. A seeded row keeps the public id it got: an adopted row (one that predates the seed keys and matched by name) and a row seeded before ids were deterministic keep their random id, since recipe mentions, revision snapshots and variations name catalogue entries by public id. Matching across instances therefore goes by seed key first and never relies on equal public ids alone.
3. `GET /api/v1/web/resolve/{public_id}` answers what a public id opens: `{kind, id, route}`, with the public id of the page's row and its frontend path, never an internal id. The port is `IPublicIdResolver` with `IPublicIdAccess` (`platform/ports/outbound/repositories/public_id_resolver.py`), the adapter `SqlAlchemyPublicIdResolver` (`platform/adapters/outbound/persistence/public_id_lookup.py`), which probes every registered table in one `UNION ALL` query, and the use case `ResolvePublicId`. The web app opens such links at `/r/<public id>` ([frontend-conventions.md section 3](frontend-conventions.md#3-styling-and-the-look)), which follows the answered route.
4. Each package registers its tables (`register_public_id_sources` with a `PublicIdSource` per table) and the read rule and page of each kind (`deps.register_public_id_access`) from the composition root, so Platform never imports the cookbook (`bootstrap/public_ids.py`). A child row names the joins to its parent and resolves to the parent's page: a step, an ingredient or equipment line and a revision to their recipe, a shopping item to its list.
5. The answer applies the read rule of the kind it found (`can_view_recipe`, `can_view_variation`, list membership, household membership). Whatever the user may not open answers 404 exactly like an unknown or malformed id, so resolving never reveals that a private row exists. A personal record (a note or rating) names its owner column and resolves for its owner only. A table that is not registered never resolves, nor does a kind without a rule; units, tags, categories, families, equipment, cook events, meal plan entries, food restrictions and every Platform table are deliberately left out.
6. `instance_id` identifies the instance to others. It is created at first start, never changes (also not with a new domain), and the admin host reading shows it (`GET /admin/host`).
7. Recipes carry `origin_instance_id` and `origin_public_id`, the source of an imported or mirrored recipe: set together or not at all (`ck_recipes_origin_pair`), unique together (`uq_recipes_origin`). The recipe's own `public_id` is always its own.
