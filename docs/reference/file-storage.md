# file storage

How images and documents are stored and served. The concept is in [CONTRIBUTING.md section 3.6](../CONTRIBUTING.md#36-file-storage); why there are three storage providers with Postgres as the default is in [ADR 0002](../adr/0002-file-storage-providers.md).

- [1 the port](#1-the-port)
- [2 accepted files](#2-accepted-files)
- [3 serving](#3-serving)
- [4 storage providers](#4-storage-providers)
- [5 moving between providers](#5-moving-between-providers)

## 1 the port

1. `IStoredFileRepository` is the storage port. It writes the metadata to `stored_files` and hands the bytes of each variant (`original`, `thumbnail`) to the active content store (`IFileContentStore`, section 4), so listing files or checking an ETag never reads content.
2. Deleting a file deletes its row and its content: by cascade with the `postgres` provider, through the content store with the others.
3. A feature that owns files (a recipe's photos) keeps the file's id in its own table; the file storage knows nothing about its users.
4. A user's avatar is an image like any other, named by `users.avatar_file_id`. `PUT /api/v1/web/users/me/avatar` stores the new image and deletes the previous file in the same transaction, `DELETE` removes it, and deleting the account, by an administrator or by the user, deletes the avatar file with it. Every person reference in the signed-in API (`PersonRef`, `UserResponse`) carries `avatar_id`, so the avatar shows wherever the name does; the frontend shows the thumbnail and falls back to the initials.
5. `FileAccess` (`platform/application/services/file_access.py`) decides who reads a file on the session routes. A signed-in user reads their own uploads, every avatar (signed-in members see every member's name), the branding images, and whatever a feature's `IFileAccess` rule allows. The cookbook registers one from `src/bootstrap/cookbook_hooks.py`: a recipe image opens for whoever may see one of the recipes that use it (`can_view_recipe`), and an avatar a paired instance sent with an author's name opens for whoever may see the mirror that shows it. Anything else answers 404 like an unknown id, so a file id alone never opens a private recipe's photo.
6. Putting an existing image on a recipe follows the same rule. The editor may keep the images the recipe has, take back the images of the revision they restore, and add an image they may read; an avatar or branding image is refused, since deleting the recipe would delete it. A refused image answers 404 `StoredFileNotFoundError`. A branding image must be one the administrator may read, so the sign-in background never publishes a private photo.
7. `DELETE /api/v1/web/files/{id}` is for an upload nothing uses yet, such as an image picked in the editor and dropped again: only the uploader may delete it (403 otherwise), and a file in use answers 409 `FileInUseError`. A file in use goes with what uses it: the recipe, the avatar or the branding.
8. A file is in use while something refers to it: a user's avatar (`users.avatar_file_id`), the sign-in background of the general settings, or a record of a feature, through the `referenced` method of its `IFileAccess` rule. For the cookbook that is a recipe cover, a step image, and a mirror's images and the author avatars a peer sent with it (`recipe_mirrors.files` and `extras`). The history counts only for the sweep of point 9 (`referenced(..., history=True)`): the cover or a step image of a revision snapshot keeps the file from being swept, so restoring the revision puts the image back, but its uploader may still delete it, and a restore then drops the missing image. A new kind of record that keeps a file id must answer for it there, or the sweep of point 9 deletes its files.
9. Uploads nothing uses are swept. The editor uploads an image as soon as it is picked, so a draft that is discarded, or never saved, leaves a file no record names. The nightly jobs ([admin-area.md section 10](admin-area.md#10-retention-and-the-nightly-jobs)) run `SweepUnusedFiles` (`application/use_cases/files/sweep_unused_files.py`) after the retention purge: every file created more than 30 days ago that is not in use (point 8) is deleted, documents included. The grace period is fixed in code (`UNUSED_FILE_GRACE`) and outlasts an editor draft the user comes back to weeks later; the recipe editor keeps its drafts on the device without a time limit, so when it restores a draft it asks for each image the draft added and removes those the sweep has deleted (`useEditorDraft`'s `images` option), and the draft notice says so. An image that only an old revision names goes once the retention purge has removed that revision.
10. The sweep is safe against a file being attached while it runs. It finds the candidates, locks each row (`SELECT ... FOR UPDATE SKIP LOCKED`, so a row that a transaction is referring to right now is skipped), checks the locked files again and deletes the rows of those still unused, all in one transaction. A reference committed before the locks is seen by the second check; one written after them waits for the commit and then fails on the missing row instead of losing its image. The content of the `local` and `seaweedfs` providers is deleted after the commit, so a failed commit never leaves a row without content. The nightly job logs how many files and bytes it removed, and a warning when a provider failed to delete content; the leftover content is never served (section 4 point 5).

## 2 accepted files

1. Images: JPEG, PNG, WebP and GIF, up to 25 MB. Every image is decoded and encoded again as WebP (quality 82) with its longest edge at most 2560 px, plus a WebP thumbnail of at most 480 px. EXIF orientation is applied to the pixels first; EXIF, GPS, XMP and ICC data are dropped. Animated GIFs keep their first frame. The decoder refuses images over 64 megapixels.
2. Documents: PDF up to 20 MB, stored as uploaded after its `%PDF-` signature was checked, with the type `application/pdf` set by the server rather than the one the client declared.
3. The upload route reads at most one byte more than the larger of the two limits, so an oversized body is refused with 413 without being read into memory whole.
4. Everything else, HTML and SVG in particular, is refused with 415.
5. Uploading needs a session, and reading follows section 1 point 5. Agents upload recipe images through the `attach_recipe_image` tool, which needs `write:recipes`.

## 3 serving

1. `GET /api/v1/web/files/{id}/content` serves the original or, with `variant=thumbnail`, the thumbnail (a document has none and serves the original). With the `seaweedfs` provider it answers `307` with a presigned URL instead, after the ETag check (section 4).
2. The ETag is the SHA-256 of the served bytes; a matching `If-None-Match` answers 304.
3. Every response carries `X-Content-Type-Options: nosniff`, `Cache-Control: private, max-age=3600, must-revalidate` and a `Content-Disposition` with both filename forms and CR/LF removed. `inline` is honoured only for raster images and PDFs.
4. The security headers middleware adds `Content-Security-Policy: default-src 'none'` to every API response, so a file a browser opens as a document can run no script; a PDF gets only `frame-ancestors 'none'`, which its viewer needs.
5. Three routes serve files without a session. The sign-in background serves only the file the general settings name, at `GET /api/v1/public/branding/login-background`.
6. `GET /api/v1/public/recipes/{recipe_id}/images/{image_id}` serves an image of a public recipe to visitors who are not signed in: only the recipe's cover or one of its step images, only while the recipe is public in effect (checked on every request), and only the thumbnail, never the original; a file without a thumbnail answers 404 like an unknown one. It is served as `image.webp`, inline, with `Cache-Control: private, max-age=300, must-revalidate`, so no shared cache keeps it after the recipe stops being public, and `X-Robots-Tag: noindex` ([cookbook.md](cookbook.md) section 6e).
7. `GET /api/v1/public/recipes/{recipe_id}/author-avatar` serves the thumbnail of the author's avatar under the same rule as the author's name: only while the recipe is public in effect and its owner shows their name on public recipes. The recipe says so in `author_avatar`; the file's id never appears on the public pages. It is served like the recipe images of point 6.

## 4 storage providers

`STORAGE__PROVIDER` picks where the bytes go; `src/platform/adapters/outbound/storage/` holds the three stores and the factory.

1. `postgres`, the default: `stored_file_contents`, written in the request's transaction, covered by the nightly dump.
2. `local`: one file per variant at `files/<public id>/<variant>` below `LOCAL_STORAGE__BASE_DIR` (the `files` volume, `/app/files` in the image), written to a `.partial` name and renamed.
3. `seaweedfs`: objects at the same key in `STORAGE__BUCKET_NAME` (`objects`, the only bucket the bundled SeaweedFS creates) over the S3 API at `STORAGE__ENDPOINT_URL`, with `STORAGE__ACCESS_KEY`, `STORAGE__SECRET_KEY`, `STORAGE__REGION` and `STORAGE__USE_SSL`. boto3 is imported when the store is first built.
4. Presigned URLs are signed for `STORAGE__PUBLIC_ENDPOINT_URL`, the deployment's own origin, last `STORAGE__PRESIGNED_URL_SECONDS` (3600), repeat the stored content type and the disposition rules of section 3 (inline only for raster images and PDF) and use path-style addressing, `<origin>/objects/<key>`. The frontend's nginx forwards `/objects/` to SeaweedFS for GET and HEAD only, with `nosniff` and a sandboxing CSP; every write goes from the backend to SeaweedFS directly.
5. The local and S3 providers write outside the database transaction. A rolled-back upload can leave content that no row names; it is never served, since every read starts from a row.
6. The boot guard refuses the `seaweedfs` provider without an endpoint, keys or, outside debug mode, a public endpoint or with the sample secret.

## 5 moving between providers

Changing `STORAGE__PROVIDER` moves no file. The storage CLI (`src/bootstrap/cli/storage.py`, `MoveStorage` in `application/use_cases/files/move_storage.py`) does:

1. `copy --to <provider> [--from <provider>]` reads every variant of every file from the source (default: the active provider), checks it against the hash in its metadata, writes it to the target and reads it back to check again. Variants already on the target with the right hash are skipped, so it can run again.
2. `verify [--provider <provider>]` checks that a provider holds every variant with the right hash.
3. `remove-source --from <provider>` deletes the content from an old provider, only after `verify` passed on the active one, and refuses the active provider itself.

The operator steps are in [OPERATIONS.md section 2.2](../OPERATIONS.md#22-moving-files-to-another-provider).
