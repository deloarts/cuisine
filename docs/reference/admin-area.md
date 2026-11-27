# admin area

The backend behind the admin area's Host, General, Storage and backup and Notifications tabs: what each reading means, the branding and display settings, webhooks, the banner and in-app notices. Users, groups and the security settings are in [auth.md](auth.md); file storage itself is in [file-storage.md](file-storage.md). The operator view is [OPERATIONS.md](../OPERATIONS.md).

- [1 permissions](#1-permissions)
- [2 host](#2-host)
- [3 storage and backup](#3-storage-and-backup)
- [4 general settings](#4-general-settings)
- [5 webhooks](#5-webhooks)
- [6 banner](#6-banner)
- [7 in-app notices](#7-in-app-notices)
- [8 mail](#8-mail)
- [9 maintenance mode](#9-maintenance-mode)
- [10 retention and the nightly jobs](#10-retention-and-the-nightly-jobs)
- [11 back up now and restore guidance](#11-back-up-now-and-restore-guidance)
- [12 log viewer](#12-log-viewer)
- [13 feature switches](#13-feature-switches)
- [14 legal pages and the privacy statement](#14-legal-pages-and-the-privacy-statement)
- [15 consents](#15-consents)
- [16 ports for the cookbook](#16-ports-for-the-cookbook)
- [17 peers](#17-peers)

## 1 permissions

1. Every reading and every admin section needs `read:settings`; every change needs `write:settings`. No new permission exists for the admin area.
2. The public surface (`/api/v1/public`) answers without a session: the instance info with branding and display defaults, the active banner, the sign-in background for the login page, the web app manifest, the legal pages, robots.txt, and the public recipe pages with their own rate limit ([cookbook.md](cookbook.md) section 6e).
3. Changes to webhooks, the banner, notices and every settings section land in the security log as `settings_changed`, with the section and the changed field names, never values.

## 2 host

1. `GET /api/v1/web/admin/host` reads the machine live through psutil and probes the database and Redis on every call; nothing is stored.
2. CPU, memory and disk are the container's view: inside Docker the disk reading is the volume the image runs on, the memory reading the host's unless the container has a limit.
3. A service that does not answer reports `down` with a short category (the exception's class name), never the raw message.

## 3 storage and backup

1. `GET /api/v1/web/admin/storage` reports the active storage provider and whether it answers its check, the database size (and the largest tables on Postgres), file counts and bytes by kind, and the backup sidecar's dumps.
2. The backend sees the dumps through the `backups` volume mounted read-only at `BACKUP__DIR`; it never writes there. `BACKUP__KEEP_DAYS` and `BACKUP__HOUR` mirror the sidecar's settings for display. With `BACKUP__DIR` empty (the dev setup) the backups are not visible.
3. The warnings, in the order `src/platform/domain/services/storage_rules.py` gives them: `files_on_database_host` (the `local` provider, or `seaweedfs` reached as `seaweedfs`, `localhost` or a loopback address), `files_not_in_backup` (any provider but `postgres`), `backups_not_visible`, and with visible backups `no_backup_yet` or `backup_stale` (the newest dump is older than 26 hours), then always `backups_on_database_host`, since the sidecar writes on the same machine.

## 4 general settings

1. The `general` section carries, besides the instance name and default language, the branding (`accent_color` as `#rrggbb` or empty, `login_background_file_id`) and the display defaults (`unit_system`, `date_format`, `time_format`, `first_day_of_week`). The enum values are in `src/platform/domain/value_objects/display.py`; `unit_system` has only `metric` today.
2. The sign-in background is uploaded with `POST /files` like any image and its id saved in the section; saving refuses an id that is not a stored image. `GET /api/v1/public/branding/login-background` serves exactly that file without a session, with its ETag, and 404 without one. Uploads become WebP of at most 2560 px ([file-storage.md](file-storage.md)), which is large enough for a full-screen photo.
3. `GET /api/v1/public/manifest.webmanifest` is the web app manifest that lets a phone install the instance as an app. It carries the instance name as `name` and `short_name`, the default language as `lang`, the accent colour as `theme_color` (the frontend's default `#c2410c` without one) and the fixed icons in `frontend/public/icons/`. It is public, since browsers fetch it without credentials, and may be cached for five minutes. The frontend side is in [frontend-conventions.md section 3](frontend-conventions.md#3-styling-and-the-look).
4. `GET /api/v1/public/info` repeats the branding and display defaults, with `login_background_key` (a short hash of the background's id, or null) instead of the background's. The key changes with the image, so the sign-in screen puts it in the URL and never shows a cached copy of the previous photo.
5. The nutrition data integration, the privacy defaults and the shopping list settings have their own sections (`/settings/integrations`, `/settings/privacy`, `/settings/shopping`) that the General tab shows. The shopping section holds `bought_window_hours` (1 to 720, default 12) and `idle_list_days` (0 to 3650, default 30, 0 turns idle deletion off); the cookbook reads and enforces both ([cookbook.md section 7](cookbook.md#7-shopping-lists-and-live-updates)).

## 5 webhooks

1. A subscription has a name, an http or https URL, the events it wants and a signing secret. The secret is shown only in the answer to create and rotate, stored encrypted, and signs every delivery the Standard Webhooks way (`webhook-id`, `webhook-timestamp`, `webhook-signature: v1,<base64 HMAC-SHA256 of "{id}.{timestamp}.{body}">`, plus `X-Cuisine-Event`).
2. The event catalogue is `src/platform/domain/value_objects/webhook_event.py`. Platform registers `user.created`, `user.deleted` and `settings.changed`; the composition root registers the cookbook's events (`src/bootstrap/webhook_events.py`, today `recipe.published` and `recipe.deleted`). A subscription may only name registered events; `GET /admin/webhooks/events` lists them.
3. A use case publishes through `WebhookPublisher` (`Platform.webhooks` in the dependency providers) inside its own transaction, so a delivery exists exactly when the change it reports was committed. The `notifications` settings section can switch every webhook off.
4. The webhook worker (`src/bootstrap/webhook_worker.py`) runs on every backend worker's event loop and sends due deliveries every 5 seconds. A delivery is claimed with a conditional update, so two workers never send it twice; one stuck in `sending` for 5 minutes goes back to `pending`.
5. A non-2xx answer or a failed request is retried after 1, 5, 30 and 120 minutes; after the fifth attempt the delivery is `failed`. A manual retry (`POST .../deliveries/{id}/retry`) sends again at once with the same `webhook-id`, so a receiver can drop duplicates, and does not count as an attempt. `POST .../test` sends a `ping` that is never retried.
6. The target guard, which checks peer URLs too ([peering.md](peering.md)), refuses URLs with credentials, the stack's own service names, localhost, loopback, link-local (including the cloud metadata address), multicast and reserved addresses, checking every address a host resolves to. Private network addresses pass unless `allow_private_webhook_targets` is off. Redirects are not followed and the answer's body is never read; the log keeps the status, the duration and a short error category.
7. Privacy: `user.deleted` carries no data about the person. A delivery that describes a user (`user.created`) is linked to that user and deleted with them, so the log keeps no trace of a deleted account. `settings.changed` names the section and fields, never their values.
8. The delivery log keeps finished deliveries for 30 days.
9. Peer channels are not webhooks. They reuse the pattern (an outbox written in the change's transaction, a worker, conditional claims, Standard Webhooks headers, the target guard) but have their own tables and worker, sign with the peer secret, retry forever instead of failing after the fifth attempt, are never switched off after failures, and are not listed among the webhooks or written to the delivery log; the peer page shows each channel's last delivery instead. The webhooks switch of this section does not affect them; the `peering` feature switch does ([peering.md section 11](peering.md#11-peer-channels)).

## 6 banner

1. One banner, in the `banner` settings section: `enabled`, `severity` (`info`, `warning`, `critical`), a message per content locale of at most 500 characters, an optional `starts_at`/`ends_at` window and `dismissible`.
2. `GET /api/v1/public/banner?locale=` answers the active banner in the requested locale, else en-GB, else any, or `null`. Its `key` changes whenever the content changes, so a dismissal the frontend stores under the old key does not hide a new message.

## 7 in-app notices

1. A notice has a title and a body (the recipe text's Markdown subset) per content locale, and is shown to every active person, not service accounts, once, until they acknowledge it. Switching a notice off hides it and keeps its acknowledgements; editing keeps them too, so a notice whose meaning changed should be a new one.
2. `GET /notices/pending` lists the signed-in user's unacknowledged active notices, oldest first, in their language (or `?locale=`); `POST /notices/{id}/acknowledge` is idempotent.
3. `GET /admin/notices/{id}/acknowledgements` lists who acknowledged when and who has not yet. Acknowledgements are deleted with their user.

## 8 mail

1. Mail is optional. With it off, a test mail answers 400 `MailNotConfiguredError`, and operational alerts and the welcome mail do nothing; nothing else in the app mails.
2. The `mail` section: server, port, `security` (`starttls`, `tls` for SSL on port 465, `none`), user, encrypted password, `sender` and `sender_name` (the From header), `reply_to`, `verify_certificate` (off for a home relay with a self-signed certificate), `send_limit_per_hour` (counted per backend worker; 0 lifts it) and `alert_recipients`.
3. Mail kinds and their variables are declared once in `src/platform/domain/services/mail_templates.py`: `test_mail`, `operational_alert` and `user_created`, the welcome mail an active account gets in its language right after an administrator creates it. The welcome mail names the sign-in address and a link to the login page but never the password, which the administrator hands over; it is sent after the commit and never fails the creation, a failure is logged. Each kind ships `<kind>.<locale>.html` files in `src/platform/adapters/outbound/external/mail/templates/`, whose `<title>` is the subject.
4. A send uses the administrator's template of the first language in the chain (recipient's language, instance default, en-GB) with a non-blank body, else the packaged file. Templates render with Jinja in a sandbox with autoescaping, so a value can never inject markup; a plain-text part is derived from the HTML.
5. The editor's endpoints under `/settings/mail/templates`: list (with defaults and `customized`), save per language (a blank body returns to the default; a template that does not render with the kind's sample values is refused), preview with the sample values, the packaged default, and HTML file import (`<title>` required) and export, which round-trip.
6. The alert catalogue (`src/platform/domain/value_objects/mail.py`, `GET /settings/mail/alerts`): `backup_failed`, `webhook_disabled` (a webhook switched off after its last three deliveries failed for good), `maintenance_switched`, `storage_warning` (a storage and backup warning that was not there at the last check). An alert never raises; a failure to mail it is logged.

## 9 maintenance mode

1. While the `maintenance` section is on, every write (anything but GET, HEAD and OPTIONS) and the whole MCP surface answer 503 with the code `MaintenanceModeError` and the message in the reader's language. Signing in and out, the public surface, the probes and `PUT /settings/maintenance` stay open, so an administrator can switch it off.
2. Each backend worker reads the state at most every 3 seconds; the worker that switches it sees the change at once.
3. `GET /api/v1/public/info` reports `maintenance {enabled, message, since}` for the banner.
4. From the server, for upgrades and restores: `docker compose exec maintenance /entrypoint.sh admin maintenance on --message "..."`, `off` and `status`.

## 10 retention and the nightly jobs

1. The `retention` section, in days, 0 keeping forever: security log 365, agent calls 90, webhook deliveries 30, recipe revisions 365 (the cookbook enforces the last).
2. `src/bootstrap/nightly_jobs.py` runs on each worker's event loop, checks hourly and runs once a day: the retention purge, the sweep of uploads nothing uses ([file-storage.md section 1 point 9](file-storage.md#1-the-port)), then the checks that mail `backup_failed` once per failed sidecar run and `storage_warning` once per new warning. The time of the last run and what was alerted are kept in the `job_state` settings row.
3. Another package adds purge steps with `deps.register_retention_purger(factory)`, a factory that takes the session and returns `async (RetentionSettings) -> int`.
4. `src/bootstrap/shopping_jobs.py` runs the cookbook's shopping list purge the same way every 15 minutes, claiming each run through `shopping_purge_at` in the `job_state` row.

## 11 back up now and restore guidance

1. The backend and the backup sidecar share the `backup_control` volume (`BACKUP__CONTROL_DIR`, `/backup-control` in the backend, `/control` in the sidecar). `POST /admin/backups/run` writes a `request` file; the sidecar checks every 15 seconds, runs the same dump as at night, removes the request and writes `status.json` (`trigger`, `started`, `finished`, `ok`, `file`). The backend never runs `pg_dump` and needs no Docker access.
2. 202 when requested, 409 `BackupAlreadyRequestedError` while a request waits, 503 `BackupControlUnavailableError` without the shared directory (the dev setup).
3. `/admin/storage` adds `backup_now_available`, `backup_requested` and `last_run`.
4. `GET /admin/backups/restore-guidance?locale=` returns the restore steps of [OPERATIONS.md section 3](../OPERATIONS.md#3-restore) with the newest dump's name. Restoring stays a task on the server.

## 12 log viewer

1. `GET /admin/logs?level=WARNING|ERROR|CRITICAL&limit=` (`read:security_log`) lists the newest warnings and errors of the backend worker that answers, from an in-memory ring buffer of 500 entries per worker; the full log stays on stdout.
2. Every message is redacted before it is kept: the configured secret and encryption keys, the initial password, the storage secret and the database password, any `password=`, `token=`, `secret=` or `api_key=` value, bearer tokens, credentials in URLs, and Cuisine's own token, webhook secret, peer secret and invitation code formats.

## 13 feature switches

1. The `features` section is the one place for `agents`, `webhooks`, `households`, `dinner_guests`, `usda` and `peering`. Every switch is on for a fresh instance, `peering` included, since the default visibility of a fresh instance is `peers` ([cookbook.md section 6b](cookbook.md#6b-recipe-visibility)); an existing instance keeps the switches it stored. While `peering` is off, every peering route answers 404, the Peers tab is hidden and a recipe set to `peers` reads as `instance` ([peering.md section 10](peering.md#10-feature-switch-outbound-requests-and-the-security-log)). Switching `peering` changes who may receive recipes, so it publishes a new privacy statement version (section 14), and the admin area asks first. The agents, notifications and integrations sections show the same three flags as their `enabled` fields and saving either side updates both.
2. `GET /api/v1/public/info` reports them. The cookbook checks households and dinner guests through `IFeatureSwitches` (section 16).

## 14 legal pages and the privacy statement

1. The imprint and the privacy statement are versioned per content locale in `legal_versions`; publishing (`POST /admin/legal/{kind}`) adds the next version, nothing is ever edited. `GET /api/v1/public/legal/{kind}?locale=` serves the current one without a session, always, so the imprint and the privacy statement are readable by visitors of the public recipe pages (the guest layout links them); `GET /admin/legal/{kind}/versions` lists the history.
2. `GET /admin/legal/privacy/draft?locale=` writes a draft from the instance's configuration (storage provider, backup hour and `BACKUP__KEEP_DAYS` with the "gone from backups" rule, retention, agents, webhooks, USDA, mail, households, dinner guests, the deletion rules including self-deletion, and whether public recipes stay online too). Bracketed parts are the administrator's. While the `peering` feature switch is on, the draft has a "Paired instances" section: every paired instance the administrator lets users share with receives the recipes a user explicitly shares with it, every recipe set to "Paired instances" (`peers`) and every public recipe (none while public recipes are not allowed); it receives the content, the images and the variations that are as visible as the recipe, never a private variation; the author's display name goes with it only while the author's "show my name on paired cookbooks" setting is on, and the e-mail address and everything personal never leave; recipes paired instances share with this one are shown, read only, after an administrator accepted them (at once from a peer with "sync all"), and what users do with them stays on this instance.
3. The privacy mode (instance, peers, public, private, or user choice with the default visibility) is part of every rendered statement: the text's `{{ privacy_mode }}` marker is replaced by a section generated from the snapshot the version was published under, or the section is appended. The snapshot (`legal_versions.privacy_mode`) is `{mode, default_visibility, allow_public_recipes, peering_enabled}`; a version without `allow_public_recipes` or `peering_enabled` reads as off for it. The lock mode `peers` (every new recipe `peers`, locked) needs peering on; while peering is off, a `peers` default reads as `instance` and the mode as instance mode. `GET /admin/legal/{kind}/versions` answers `peering_enabled` next to `allow_public_recipes`. The section says that the mode is the administrator's decision and that whoever does not accept it cannot use Cuisine, and it ends with a "Public recipes" part: while allowed, that anyone on the internet can read a public recipe without signing in but nobody can change it there, and that the author's name is hidden unless the author switches it on; while not allowed, that no recipe can be read without signing in. Changing any privacy setting, `allow_public_recipes` included, or switching the `peering` feature on or off, publishes the same text as a new version under the new snapshot, so every user acknowledges it again.
4. Once a statement exists, a person who has not acknowledged its current version gets 403 `PrivacyAcknowledgementRequiredError` on every web, PAT and MCP request, except `GET /users/me`, `POST /users/me/privacy/acknowledge` and `/decline`, the auth routes and the public surface. Acknowledging names the version (409 `StalePrivacyVersionError` when it is not the current one); declining signs the user out. Whoever publishes a version has acknowledged it. Service accounts are never asked.
5. `GET /users/me` adds `privacy_acknowledgement_pending`, `privacy_version`, `privacy_acknowledged_version`, `privacy_mode {mode, default_visibility, allow_public_recipes}` and the consent times; `GET /api/v1/public/info` adds `privacy_mode`, `default_recipe_visibility`, `imprint_published`, `privacy_statement_published`, `allow_public_recipes` (the login page then links to "Browse public recipes") and `index_public_recipes` (true only while public recipes are allowed and the search engine switch is on).
6. `GET /admin/legal/privacy/acknowledgements` (`read:settings`) shows which person acknowledged which version: `acknowledged` lists the active people on the current version, `pending` the others with the version they acknowledged last (null when never), each with the time. Service accounts are never listed; before the first statement both lists are empty.
7. The privacy section also holds `index_public_recipes`, "let search engines index public recipes", off by default and effective only while `allow_public_recipes` is on (`PrivacySettings.indexing_allowed`). It is not part of the privacy mode: changing it alone publishes no new statement version. `GET /api/v1/public/robots.txt`, which the frontend's nginx serves as `/robots.txt`, closes everything (`Disallow: /`) unless indexing is allowed, and then opens only `/public/`, `/assets/` and `/api/v1/public/`. The public pages set the robots meta tag to match (`index, follow` or `noindex, nofollow`); every anonymous API response carries `X-Robots-Tag: noindex`.

## 15 consents

1. `health_data` and `ai_agents`, each a timestamp on the user or null. `GET /users/me/consents`, `PUT /users/me/consents/{kind}` to give one, `DELETE` to withdraw it.
2. Without `ai_agents`, a personal access token with `use:mcp` cannot be created (403 `ConsentRequiredError`), no app can be approved through OAuth, and the MCP surface refuses the person's tokens. Withdrawing revokes every `use:mcp` token of the user and ends every connected app ([auth.md section 8](auth.md#8-oauth-for-hosted-ai-clients)).
3. Withdrawing `health_data` deletes the user's allergies, intolerances and diets in the same transaction through `IHealthDataEraser`, registered by the cookbook; without a registered eraser the withdrawal is refused, so the consent never goes while the data stays. Requiring the consent before restrictions are entered is the cookbook's.

## 16 ports for the cookbook

1. `IFeatureSwitches` (`ports/outbound/feature_switches.py`): `get_features()`, implemented by the settings repository; `deps.get_feature_switches`.
2. `IInstanceFacts` (`ports/outbound/instance_facts.py`): `backup_retention(deleted_on=None)` gives `BACKUP__KEEP_DAYS` and the day data deleted then is gone from every backup (keep days plus one); `deps.get_instance_facts`. `GET /settings/backup-retention` serves the same to every signed-in user.
3. `IHealthDataEraser` (`ports/outbound/health_data_eraser.py`), registered with `deps.register_health_data_eraser(factory)`, a factory taking the session.
4. Retention purge steps, registered with `deps.register_retention_purger(factory)` (section 10).
5. Webhook events through `Platform.webhooks.publish` (section 5).

## 17 peers

1. The Peers tab (shown while the `peering` switch is on) shows this instance's `instance_id`, base URL and supported versions (`GET /admin/peers/self`), creates invitations whose link shows once with its expiry, lists and revokes open invitations, accepts another instance's invitation link, and lists the paired instances with their status, app version, negotiated protocol and format versions, capabilities, what they cannot show, paired time, last contact and switches, with refresh and revoke (confirmed). The switches dialog has "Recipes may go to this instance" (`users_may_share`), "Accept recipes from this instance", who sees accepted recipes, and "Sync all from this instance" (`sync_all`, on for a new pairing); switching sync all on offers once to accept every recipe of that peer that waits now (`POST /admin/peers/{id}/incoming-recipes/accept`, `write:settings`), rejected ones excluded.
2. Each active peer shows its channel: the last sequence sent and the highest given out, the events still waiting to be sent, the last sequence received, the events waiting in the inbound queue, the last delivery with its time, HTTP status and error category, the next attempt, the last catch-up and comparison, and the last receive error. "Sync now" (`POST /admin/peers/{id}/sync`, `write:settings`) makes the catch-up and the next delivery attempt due at once. Reading needs `read:settings`, every change `write:settings`. The rules are in [peering.md](peering.md).
3. Recipes from paired instances wait for an administrator: `GET /admin/incoming-recipes?status=pending|rejected` (`read:settings`) lists them with the peer, title, author name, whether it is new or a held update of a mirror, the sub-recipes it uses (mirrored or waiting here, or not shared) and every catalogue entry that needs a decision with a suggestion. `POST /admin/incoming-recipes/{id}/accept`, `/reject` and `/reopen` (`write:settings`) decide on it, and `GET` and `PUT /admin/peers/{id}/mappings...` read and correct the catalogue mappings of a peer. The rules are in [cookbook.md section 6f](cookbook.md#6f-sharing-with-paired-instances-and-mirrors).
