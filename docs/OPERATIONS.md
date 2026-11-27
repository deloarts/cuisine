# operating

How to keep a Cuisine instance running: backups, restores, updates, recovery and logs.

- [1 what holds the state](#1-what-holds-the-state)
- [2 storage and backups](#2-storage-and-backups)
  - [2.1 storage providers](#21-storage-providers)
  - [2.2 moving files to another provider](#22-moving-files-to-another-provider)
  - [2.3 backups](#23-backups)
  - [2.4 copying backups off the host](#24-copying-backups-off-the-host)
- [3 restore](#3-restore)
  - [3.1 maintenance mode](#31-maintenance-mode)
- [4 updates](#4-updates)
- [5 recovery commands](#5-recovery-commands)
- [6 health and logs](#6-health-and-logs)
- [7 AI agents behind Cloudflare](#7-ai-agents-behind-cloudflare)

## 1 what holds the state

Postgres holds accounts, settings, recipes, the security log and, with the default `postgres` storage provider, every uploaded photo and document ([ADR 0002](adr/0002-file-storage-providers.md)). Redis holds only login throttling counters, short-lived replay claims and live update messages, which may be lost at any time. With the default provider a database dump plus `SECURITY__ENCRYPTION_KEY` is therefore a complete backup; with the `local` or `seaweedfs` provider the file volume needs its own backup (section 2.1).

## 2 storage and backups

The admin area's **Storage and backup** tab shows the active provider, the database and file sizes, the newest dumps and warnings for the setup below.

### 2.1 storage providers

`STORAGE__PROVIDER` in the env file picks where the bytes of uploaded files go; the metadata always stays in Postgres. The exact rules are in [reference/file-storage.md section 4](reference/file-storage.md#4-storage-providers).

| Provider | Where | In the nightly dump | Pick it when |
| -------- | ----- | ------------------- | ------------ |
| `postgres` (default) | the database | yes | a household instance; one dump is the whole state |
| `local` | the `files` volume | no | the database should stay small and the machine's disks are backed up anyway |
| `seaweedfs` | an S3 store, the bundled one with `--profile seaweedfs` | no | many photos, or an object store on other hardware |

For the bundled SeaweedFS, set `SEAWEEDFS_ACCESS_KEY` and a `SEAWEEDFS_SECRET_KEY` of at least 24 characters, the same pair as `STORAGE__ACCESS_KEY` and `STORAGE__SECRET_KEY`, `STORAGE__ENDPOINT_URL=http://seaweedfs:8333` and `STORAGE__PUBLIC_ENDPOINT_URL` to the instance's own address, then start with `docker compose --profile seaweedfs up -d`. Browsers load files through the instance's address at `/objects/`, read-only.

With `local` or `seaweedfs`, back up the `files` or `seaweedfs` volume, or the remote bucket, next to the dumps, and restore both together; the tab warns until then, and also when the files share the database's machine.

### 2.2 moving files to another provider

Changing `STORAGE__PROVIDER` alone moves no file: files on the old provider become unreachable. Move them with the storage CLI, from the backend or the maintenance container:

```bash
docker compose exec backend /entrypoint.sh storage copy --to local
# set STORAGE__PROVIDER=local in the env file, then
docker compose up -d backend
docker compose exec backend /entrypoint.sh storage copy --from postgres --to local
docker compose exec backend /entrypoint.sh storage verify
docker compose exec backend /entrypoint.sh storage remove-source --from postgres
```

`copy` checks every file against its hash on both sides and can run again; the second run catches files uploaded before the restart. `remove-source` deletes from the old provider only after `verify` found every file intact on the active one, and never touches the active provider. Take a dump on demand (section 2.3) first.

### 2.3 backups

The `backup` service writes a compressed `pg_dump` every night at `BACKUP_HOUR` (UTC, default 3) into the `backups` volume, or into `BACKUP_DIR` on the host when set, and removes dumps older than `BACKUP_KEEP_DAYS` (default 14). A dump is written to a `.partial` file first and renamed only once complete.

Copy the dumps off the host (section 2.4) and keep the encryption key in a separate place such as a password manager. **Back up now** in the admin area's Storage and backup tab asks the sidecar for the same dump at once, through the shared `backup_control` volume; the tab shows how the last run went. From the shell, a dump on demand:

```bash
docker compose exec backup sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > cuisine-manual.dump
```

### 2.4 copying backups off the host

A dump on the same machine does not survive a failed disk, so copy it to a second machine, ideally one in another building. Any file sync or backup tool works; this section names what to copy and the settings that keep the copy safe.

**What to copy.** Set `BACKUP_DIR` to a host directory such as `/srv/cuisine/backups`, so the dumps are ordinary files a sync tool can reach. With the `local` storage provider, also copy the `files` volume (see below). Never sync the `postgres` or `seaweedfs` volume of a running instance: their files change while the sync reads them, and the copy may not start or may be silently damaged. Back up a SeaweedFS bucket through its S3 API instead, for example with `rclone`. The `redis` volume needs no backup. Keep the env file out of the synced folder and store it, with `SECURITY__ENCRYPTION_KEY`, in a password manager.

**Rules for any sync tool.**

1. Sync one way, from the server to the backup machine. The receiving side must not be able to change or delete anything on the server, or a mistake or ransomware there reaches the server too.
2. Ignore `*.partial`. The backup sidecar and the `local` provider write to a `.partial` name first and rename the file once it is complete, so a half written file is never worth copying.
3. A mirror is not a history. When the sidecar removes dumps older than `BACKUP_KEEP_DAYS`, a mirror removes them too, and a damaged dump replaces the good one. Keep older copies on the receiving side with the tool's file versioning, the receiving machine's own snapshots, or a versioned backup tool such as `restic`.

**Resilio Sync.** Add `BACKUP_DIR` on the server and connect the backup machine with the folder's read-only key, which satisfies rule 1. Add `*.partial` to the folder's `.sync/IgnoreList`. Files the server deletes or replaces are moved to `.sync/Archive` on the receiving side and kept there for the period set in the folder's preferences; lengthen it when the archive is the only history you keep.

Resilio can run on the server as a container next to Cuisine. The official `resilio/sync` image ships only an x86-64 build, so on a Raspberry Pi or another ARM machine use the LinuxServer.io image, which is built for `amd64` and `arm64`. Put it in a `docker-compose.override.yml` beside `docker-compose.yml`, so `docker compose up -d` starts it with the rest and updates of Cuisine's compose file never overwrite it:

```yaml
services:
  resilio-sync:
    image: lscr.io/linuxserver/resilio-sync:<version tag>
    restart: unless-stopped
    environment:
      PUID: "1000"
      PGID: "1000"
      TZ: Etc/UTC
    ports:
      - "127.0.0.1:8888:8888"
      - "55555:55555/tcp"
      - "55555:55555/udp"
    volumes:
      - resilio_config:/config
      - ${BACKUP_DIR:-backups}:/sync/cuisine-backups
      # Only with the local storage provider, bound as shown below:
      # - /srv/cuisine/files:/sync/cuisine-files

volumes:
  resilio_config:
```

Pick a version tag from the image's tag list rather than `latest`, so an update is a deliberate change. The web UI listens on the server's loopback address only; reach it through an SSH tunnel (`ssh -L 8888:localhost:8888 cuisine-host`), create the account it asks for on first start, then add `/sync/cuisine-backups` as a folder. Resilio keeps its folder metadata in a `.sync` directory inside each shared folder, so the folders must be writable for the container's user: the backup sidecar writes the dumps as root, so give the directory to UID 1000 once with `chown 1000:1000 /srv/cuisine/backups` (the sidecar still writes there as root). The backend already writes the `files` volume as UID 1000. Port 55555 carries the sync traffic and has to be reachable from the backup machine; Resilio falls back to its relay servers when it is not.

**Syncthing.** Share `BACKUP_DIR` as a "Send Only" folder on the server and accept it as "Receive Only" on the backup machine. Put `*.partial` in the folder's `.stignore` and turn on staggered file versioning on the receiving side.

**rsync.** Pull from the backup machine on a schedule, so the server needs no access to it. `--delete` is left out on purpose, so the copy keeps dumps the server has already removed:

```bash
rsync -a --exclude '*.partial' cuisine-host:/srv/cuisine/backups/ /backup/cuisine/
```

**Cloud storage.** `rclone` copies the folder to most providers, and its `crypt` remote encrypts the files before they leave the machine. `restic` stores encrypted, deduplicated snapshots with retention rules such as seven daily and twelve monthly. Dumps of the `postgres` provider are compressed and hold every photo, so they deduplicate poorly and each one costs its full size.

**The `files` volume of the `local` provider** can be synced while the instance runs, unlike the database: each file is written once under a new name and never changed. To reach it from the host, bind it to a host directory with a `docker-compose.override.yml` next to `docker-compose.yml`:

```yaml
volumes:
  files:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /srv/cuisine/files
```

Docker keeps an existing volume as it is, so for an instance that already has files, stop it, copy the old volume's content to `/srv/cuisine/files`, remove the old volume and start again. Restore the files together with the dump of the same night or a later one: a file on disk that no row names is never served, while a row whose file is missing shows a broken image.

**Check that it keeps working.** The admin area's Storage and backup tab shows the newest dump on the server. On the backup machine, a scheduled check that warns when the newest `cuisine-*.dump` is older than about 26 hours catches a stopped sidecar or a broken sync. Restore one copy on another machine now and then (section 3), since only a restore proves that the dump and the key belong together.

## 3 restore

Restoring replaces the whole database. Stop the services that use it, restore into an empty database, then start them again:

```bash
docker compose stop backend frontend
docker compose exec -T postgres sh -c 'dropdb -U "$POSTGRES_USER" "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'
docker compose exec -T postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' < cuisine-20261121-030000.dump
docker compose up -d
```

The env file must carry the same `SECURITY__ENCRYPTION_KEY` as when the dump was taken. With a different key the instance still starts, but TOTP secrets and the SMTP password load as unset: affected users set up two-factor authentication again and the mail password has to be entered again.

### 3.1 maintenance mode

Switch the app to read-only before a restore or a risky update, so nobody writes in between: in the admin area under **Operations**, or from the server with

```bash
docker compose --profile maintenance up -d maintenance
docker compose exec maintenance /entrypoint.sh admin maintenance on --message "Back at 9."
docker compose exec maintenance /entrypoint.sh admin maintenance off
```

Every page shows the banner, writes answer 503, and signing in stays possible.

## 4 updates

With `CUISINE_VERSION` pinned to a minor, an update is:

```bash
docker compose pull
docker compose up -d
```

The backend migrates the database before it starts. Read the release notes first; take a dump on demand (section 2) before a minor update. Moving to a new minor means changing `CUISINE_VERSION` in the env file.

## 5 recovery commands

The backend image carries an admin CLI for the cases the UI cannot fix, such as a forgotten administrator password or a lost authenticator:

```bash
docker compose exec backend /entrypoint.sh admin reset-password <email>
docker compose exec backend /entrypoint.sh admin reset-totp system
```

Both take the account's e-mail address, or `system` for the system account, and sign the account out everywhere. The new password is read from the terminal, never from the command line. The system account's password comes from `INIT__PASSWORD`: every start syncs the account back to the `INIT__` values, so a forgotten system password is fixed by setting `INIT__PASSWORD` and restarting the backend, and `admin reset-password system` lasts only until the next start. The system account's two-factor authentication is mandatory and cannot be reset in the app, so `admin reset-totp system` is the only way back after a lost authenticator; the next sign-in shows a new QR code. When the backend itself does not start, run the same commands in the maintenance sidecar, which never migrates or starts the app:

```bash
docker compose --profile maintenance up -d maintenance
docker compose exec maintenance /entrypoint.sh admin reset-totp system
docker compose --profile maintenance stop maintenance
```

## 6 health and logs

`/health` answers as long as the backend process runs; `/ready` also checks the database and Redis and answers 503 when either is down. Both are reachable through the frontend's nginx. Every container logs to stdout with a size cap (`docker compose logs -f backend`); `LOG_FORMAT=json` writes one JSON object per line for a log aggregator. Sign-ins and account changes are in the security log under **Settings → Security log**.

## 7 AI agents behind Cloudflare

Hosted AI apps (ChatGPT, claude.ai) call Cuisine from their own servers, without a browser, when they discover, register, fetch tokens and call tools. Behind Cloudflare these paths must therefore pass without a challenge:

- `/.well-known/oauth-*`, the discovery documents;
- `/api/v1/oauth/*`, registration, tokens and revocation;
- `/api/v1/mcp`, the tool calls.

Keep them out of any Cloudflare Access application, and add a WAF custom rule that skips Bot Fight Mode, managed challenges and rate limiting rules for them (for example `starts_with(http.request.uri.path, "/.well-known/oauth-") or starts_with(http.request.uri.path, "/api/v1/oauth/") or http.request.uri.path eq "/api/v1/mcp"`). Cuisine authenticates and rate limits these requests itself. The consent page `/oauth/authorize` is opened by a person's browser and may stay behind the usual protection.

`DOMAIN` must be the public https origin, since the discovery documents and the token audience are built from it. The frontend's nginx routes the discovery documents to the backend and accepts MCP request bodies up to 41 MB, so an agent can attach a large photo; Cloudflare's own upload limit (100 MB on the free plan) is above that. Agent calls and OAuth events land in the agent call log and the security log with the client address nginx resolved, so `CUISINE_TRUSTED_PROXIES` has to cover the tunnel's address when cloudflared runs outside the stack.
