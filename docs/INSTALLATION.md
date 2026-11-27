# installing

How to set up a new Cuisine instance from the release images. It takes a Linux host with Docker, a domain name and either a reverse proxy with a TLS certificate or a Cloudflare Tunnel.

- [1 requirements](#1-requirements)
- [2 the env file](#2-the-env-file)
- [3 start the stack](#3-start-the-stack)
- [4 put it on the internet](#4-put-it-on-the-internet)
- [5 first sign-in](#5-first-sign-in)

## 1 requirements

- A Linux host with Docker Engine 24 or newer and the Compose plugin v2.20 or newer, on x86-64 or 64-bit ARM. The images are published for linux/amd64 and linux/arm64 under the same tags, so a Raspberry Pi 4 or 5 with a 64-bit OS pulls its own; a 32-bit OS is not supported. On a Raspberry Pi, a good SD card carries the household load for years; a USB SSD is faster and survives power cuts better. Either way, keep the nightly dumps on another device (`BACKUP_DIR`), since dumps on the same card fail with it.
- A domain name for the instance, served over https. Browsers only allow passkeys on https (and on localhost), and the backend refuses to start in production with a plain-http `DOMAIN`.
- About 1 GB of RAM and enough disk for the database, which holds the photos too.

## 2 the env file

Copy `docker-compose.yml` and `.env.example` to a directory on the host, for example `/srv/cuisine`, then generate the env file:

```bash
python3 scripts/create_stack_env.py --domain https://cuisine.example.com --admin-mail you@example.com
```

The script fills in a database password, the signing key, the encryption key and the first administrator's password, and prints that password once. Without a checkout, copy `.env.example` to `.env` and fill in the same values by hand; `openssl rand -hex 32` makes a key. The backend refuses to start with any sample value left in (`backend/src/platform/infrastructure/config/boot_guard.py`).

Keep a copy of `SECURITY__ENCRYPTION_KEY` somewhere apart from the server: the database stores TOTP secrets and the SMTP password encrypted with it, so a restored backup needs the same key.

The release images are published to GHCR as `ghcr.io/deloarts/cuisine/backend` and `ghcr.io/deloarts/cuisine/frontend`. `CUISINE_VERSION` names the release to run. Pin a minor such as `v0.1` to receive patch releases with `docker compose pull`, or an exact tag such as `v0.1.0`.

## 3 start the stack

```bash
docker compose up -d
docker compose ps
```

The backend applies pending migrations before it starts its workers, then seeds the system account from the `INIT__` values: the first start creates it, every later start syncs it back to them. The frontend listens on `127.0.0.1:8080` by default (`FRONTEND_BIND`, `FRONTEND_PORT`).

## 4 put it on the internet

**Behind a reverse proxy on the host** (Caddy, nginx, Traefik): forward the domain to `http://127.0.0.1:8080` and let the proxy terminate TLS and set `X-Forwarded-For` and `X-Forwarded-Proto`. The frontend trusts those headers from the external network's gateway (`CUISINE_EXTERNAL_GATEWAY`, `192.168.251.1`), which a proxy on the same host connects through, and from the cloudflared tunnel (`CUISINE_CLOUDFLARED_IP`, `192.168.251.251`). A proxy on another machine needs its address in `CUISINE_TRUSTED_PROXIES` and `FRONTEND_BIND=0.0.0.0`. The backend in turn trusts forwarded headers only from the frontend's fixed address (`CUISINE_FRONTEND_IP`, `192.168.251.250`), never from the other containers on that network. If the default subnets clash with a network on the host, set `CUISINE_INTERNAL_SUBNET` and `CUISINE_EXTERNAL_SUBNET`, and with the latter the gateway, frontend and cloudflared addresses inside it.

**Through a Cloudflare Tunnel**: create a tunnel in the Cloudflare dashboard with the public hostname pointing at `http://frontend:80`, put its token into `TUNNEL_TOKEN` and start the profile:

```bash
docker compose --profile cloudflare up -d
```

No port on the host needs to be open then.

## 5 first sign-in

Open the domain and sign in as `system` with the printed password. The first sign-in asks you to set up two-factor authentication, which the system account cannot do without, and its sessions end 15 minutes after sign-in. The system account is meant for administration only, so create a personal account for cooking. Then, in this order:

1. Change the password under **My account → Security**.
2. Under **Settings → General**, name the cookbook and pick the default language.
3. Under **Settings → Mail**, enter the mail server and send a test mail, if the instance should send mail.
4. Under **Groups**, look through the default groups the first start created (Cooks, Kitchen helpers, Curators, Editors, Administrators and the sharing circles Family and Friends), change or delete them to suit the instance, and under **Users** create the accounts and put each person into the groups they need.

[OPERATIONS.md](OPERATIONS.md) continues with backups and updates.
