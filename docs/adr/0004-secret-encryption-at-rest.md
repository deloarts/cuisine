# 0004 encrypt readable secrets at rest with a dedicated key

- Status: accepted
- Date: 2026-11-21

## context

Some secrets must be read back in plaintext because Cuisine uses them: users' TOTP secrets, the SMTP password, the USDA API key and the webhook signing secrets. They cannot be hashed like passwords. Stored in plaintext they leak through every database dump and backup, and with the default Postgres file storage ([ADR 0002](0002-file-storage-providers.md)) the dumps are the whole backup.

## decision

These values are encrypted with Fernet under a key derived by HKDF-SHA256 from `SECURITY__ENCRYPTION_KEY`, which is separate from the signing key, and carry an `enc:v1:` prefix. Columns use the `EncryptedString` type, so entities and use cases see plain values; the mail password and the USDA API key are encrypted inside their settings JSON. `SECURITY__ENCRYPTION_KEY_PREVIOUS` keeps an old key readable during a rotation. A production backend refuses to start without a strong key or with the signing key reused (`boot_guard.py`).

## consequences

A dump alone no longer reveals the secrets; a compromised host still does, since the key sits next to the app. A value no configured key decrypts loads as unset and logs an error, so losing the key means re-enrolling two-factor authentication, re-entering the mail password and the USDA key, and rotating every webhook secret. The key therefore has to be kept apart from, and as safely as, the backups.
