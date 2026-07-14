# Dark Tunnel Config Decryptor Bot

A Telegram bot that unlocks Dark Tunnel `.dark` config exports: it decodes the
`darktunnel://` URI, AES-CFB decrypts the outer and inner MessagePack blobs,
and re-encodes an "unlocked" `.dark` file for the user — with a force-join
gate requiring channel membership before use.

## Folder structure

```
telegram-bot/
├── app/
│   ├── __init__.py
│   ├── bot.py              # Pyrogram client factory + handler wiring
│   ├── config.py           # Env-driven configuration + logging setup
│   ├── crypto_utils.py      # AES-CFB decrypt + flexible base64 decode
│   ├── dark_config.py       # Core parse/decrypt/unlock pipeline
│   ├── force_join.py        # Channel-membership check + keyboard
│   ├── handlers.py          # /start, file upload, callback handlers
│   ├── messages.py          # All user-facing text templates
│   └── msgpack_reader.py    # Dependency-free MessagePack decoder
├── main.py                  # Entrypoint with auto-restart loop
├── requirements.txt
├── .env.example
├── .gitignore
├── Dockerfile
├── Procfile                 # Heroku-style `worker` process
├── render.yaml               # Render Blueprint (background worker)
├── fly.toml                   # Fly.io app config
├── railway.json                # Railway deploy config
└── README.md
```

## What changed from the original script

- Split a single 432-line file into focused modules (config, crypto, msgpack,
  dark-config pipeline, handlers, messages).
- **Hardcoded `API_ID`, `API_HASH`, `BOT_TOKEN` removed** — all now come from
  environment variables, validated at startup with a clear error instead of a
  confusing crash.
- Removed the unused `Path`, `Document`, `quote`, `urlencode` imports and other
  dead code from the original file.
- Added structured logging (`logging` module, configurable via `LOG_LEVEL`)
  everywhere `print()` was previously used, plus `logger.exception(...)` in
  every handler and helper so failures are diagnosable in production.
- Every handler now has explicit `try/except` around it — a bad file, a
  Telegram API hiccup, or an unexpected input can no longer crash the whole
  bot process; it degrades to an error reply instead.
- Bare `except:` clauses replaced with narrow, specific exception handling.
- File downloads now go to a configurable `DOWNLOAD_DIR`, use unique temp
  filenames (`uuid4`) to avoid collisions between concurrent users, and are
  always cleaned up in a `finally` block even on failure.
- Added a file-size guard (`MAX_FILE_SIZE_MB`) to reject oversized uploads
  before they're downloaded.
- `main.py` wraps the bot in an **auto-restart loop** with exponential
  backoff: if Pyrogram crashes or disconnects unexpectedly, the process logs
  it and restarts the client rather than exiting.
- The `check_join` callback regex was anchored (`^check_join$`) to avoid
  accidentally matching unrelated callback data.
- All decrypt/unlock logic, message copy (including the original Bangla
  text), commands, buttons, and file-processing behavior are functionally
  **unchanged** — only structure, safety, and observability were improved.

## Environment variables

| Variable | Required | Description |
| --- | --- | --- |
| `API_ID` | yes | Telegram API ID from https://my.telegram.org |
| `API_HASH` | yes | Telegram API hash from https://my.telegram.org |
| `BOT_TOKEN` | yes | Bot token from [@BotFather](https://t.me/BotFather) |
| `CHANNEL_USERNAME` | no (default `minarulsensi`) | Channel username users must join |
| `CHANNEL_URL` | no (default `https://t.me/minarulsensi`) | Join link shown to users |
| `LOG_LEVEL` | no (default `INFO`) | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `SESSION_NAME` | no (default `dark_decryptor_bot`) | Pyrogram session name |
| `DOWNLOAD_DIR` | no (default `downloads`) | Where uploaded files are staged |
| `MAX_FILE_SIZE_MB` | no (default `5`) | Upload size limit in megabytes |

Copy `.env.example` to `.env` and fill in the required values for local runs.

## Commands to run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure secrets
cp .env.example .env
# edit .env with your API_ID, API_HASH, BOT_TOKEN

# 3. Run
python main.py
```

With Docker:

```bash
docker build -t dark-tunnel-bot .
docker run -d --name dark-tunnel-bot --restart unless-stopped \
  --env-file .env dark-tunnel-bot
```

## Cloudflare limitations (read this first)

**Cloudflare Workers cannot run this bot, for fundamental reasons — not just missing packages:**

1. **No Python runtime with native extensions.** Workers' Python support (Pyodide-based) runs in a WebAssembly sandbox with no access to CPython C-extensions. `cryptography` and `tgcrypto` are compiled C/Rust extensions — they cannot load in that sandbox at all.
2. **No persistent long-lived connections.** Pyrogram is *not* a webhook-only client — for MTProto it opens and holds a persistent TCP socket to Telegram's data centers. Workers execute per-request with strict CPU time limits (tens of ms to a few seconds) and cannot keep a socket open between invocations.
3. **No arbitrary filesystem.** The bot downloads user files to local disk (needed for streaming large uploads and for the decrypt/re-encode round trip). Workers have no writable filesystem — only KV/R2/Durable Objects, which would require rewriting the download path entirely.
4. **No outbound raw TCP.** Workers restrict egress to HTTP(S)/`fetch`-style requests; MTProto's binary TCP protocol used by Pyrogram isn't representable that way.

None of this is a "missing library" problem — it's an execution-model mismatch: Workers are stateless, sandboxed, short-lived request handlers, while this bot is a stateful, long-running network client.

**Closest Cloudflare-supported path, if you want to stay in the Cloudflare ecosystem:**
- **Cloudflare Containers** — Cloudflare now runs full Docker containers with real CPython, filesystem, and outbound TCP. This is the *only* Cloudflare product that can run this bot as-is (deploy the included `Dockerfile` directly). Everything else in the Workers family is out.

**Recommended deployment (free-tier friendly, keeps every feature working as-is):**
Deploy the Docker image on one of these background-worker-friendly platforms — no code changes needed:
- **Railway** — `railway.json` included, one-click deploy from Docker.
- **Render** — `render.yaml` included (background worker, not a web service — this bot has no HTTP port to bind).
- **Fly.io** — `fly.toml` included, generous free allowance, auto-restarts crashed VMs.
- **Koyeb** / **Northflank** — also support Docker background workers on free tiers.

## Deployment guide

### Railway
1. Push this `telegram-bot/` folder to a GitHub repo.
2. Railway → New Project → Deploy from GitHub → select the repo.
3. Add variables `API_ID`, `API_HASH`, `BOT_TOKEN` under Variables.
4. Railway reads `railway.json` and runs the Dockerfile automatically. Deploys as a worker (no public port needed).

### Render
1. Push to GitHub, then Render → New → Blueprint → point at this repo (`render.yaml` at repo root or `telegram-bot/render.yaml` if using a subdirectory blueprint).
2. Fill in `API_ID`, `API_HASH`, `BOT_TOKEN` when prompted (marked `sync: false`).
3. Render provisions it as a **background worker** (correct type — this bot has no HTTP server).

### Fly.io
```bash
fly launch --no-deploy   # accept the existing fly.toml
fly secrets set API_ID=xxxx API_HASH=xxxx BOT_TOKEN=xxxx
fly deploy
```

### Cloudflare Containers
```bash
# From the Cloudflare dashboard or wrangler, deploy the Dockerfile as a
# Container app, then set API_ID / API_HASH / BOT_TOKEN as container secrets.
wrangler containers deploy --dockerfile Dockerfile
```
(Exact CLI flags depend on your Wrangler version — Cloudflare Containers is a
newer product; check `wrangler containers --help` for your installed version.)

### Plain VPS / systemd (self-hosted)
```ini
[Unit]
Description=Dark Tunnel Decryptor Bot
After=network.target

[Service]
WorkingDirectory=/opt/dark-tunnel-bot
EnvironmentFile=/opt/dark-tunnel-bot/.env
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
`Restart=always` gives an outer platform-level restart on top of the bot's
own internal auto-restart loop in `main.py`.

## Security notes

- Secrets are never hardcoded — `API_ID`, `API_HASH`, `BOT_TOKEN` are read
  from the environment only, and startup fails loudly if any are missing.
- Uploaded files are validated by size before download and always removed
  after processing, even on error.
- All exception handling logs the error server-side but never leaks stack
  traces to end users — replies show a generic, safe error message.
