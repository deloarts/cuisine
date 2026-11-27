# 0002 file content goes to one of three storage providers, Postgres by default

- Status: accepted
- Date: 2026-11-21

## context

A cookbook stores photos of dishes and the odd PDF of a printed recipe: a few thousand files of a few hundred kilobytes each once images are re-encoded. Keeping them in Postgres means one dump holds the whole instance and a restore brings the photos back with the recipes that reference them, which is the right default for a household. A larger instance, or one that already runs an object store, wants its photos out of the database: a smaller dump, file reads that do not pass through the backend, and the choice to keep files on other hardware. Glados offers local and S3 storage with a bundled SeaweedFS, and its rules for presigned URLs and serving them are proven.

## decision

The metadata of every file stays in `stored_files`. The bytes go to the content store of the provider named by `STORAGE__PROVIDER`, behind the `IFileContentStore` port: `postgres` (the default, `stored_file_contents` in the request's transaction), `local` (a file per variant on a Docker volume) or `seaweedfs` (an S3 API, the bundled SeaweedFS by default, boto3 imported only when used). Re-encoding, thumbnails, EXIF stripping, content-hash ETags and the download header rules apply to every provider, since they run before the store and in the serving route. With SeaweedFS the browser loads content through presigned URLs signed for the deployment's own origin, served by the frontend's nginx at `/objects/` for GET and HEAD only, with glados's setting names and rules. A storage CLI copies content between providers, checks every variant against its hash, and removes it from the old provider only once the active one holds all of it.

## consequences

A fresh instance keeps everything in Postgres, so one `pg_dump` is a complete backup and the database grows with the photos, which suits the expected size. Choosing `local` or `seaweedfs` moves the file content out of the nightly dump, so the instance then needs a second backup and the Storage and backup tab warns about it, as it warns when the files share the database's machine. The local and S3 providers write outside the database transaction, so a rolled-back upload can leave content no row names; it is never served. Switching providers is an operator task with a restart in between, documented in [OPERATIONS.md section 2.2](../OPERATIONS.md#22-moving-files-to-another-provider).
