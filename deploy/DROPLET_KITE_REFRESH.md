# Kite session auto-refresh — runs on the DigitalOcean droplet

> **Why the droplet and not GitHub Actions?** Zerodha enforces SEBI's static-IP
> rule: every Kite Connect login/API call must originate from one registered IP.
> The droplet (`168.144.90.26`) is that whitelisted IP (it also hosts the
> tinyproxy the Fly API tunnels its Kite calls through). GitHub Actions runners
> get a **random IP**, so the TOTP login in `refresh_kite_session.py` is blocked
> there — the `cron-kite-refresh.yml` workflow was deleted for exactly this
> reason. This script must run **on the droplet**, where the IP is already
> whitelisted (so it needs **no proxy** — it calls Zerodha directly).

## What it does

`dashboard/backend/refresh_kite_session.py` logs into Zerodha with the owner's
credentials + TOTP, exchanges the request_token for a fresh access_token, and
stores it **encrypted** in the Supabase `kite_sessions` table on the **admin**
user's row. Every connected user then has live market data with no manual login.
It also writes a daily owner NAV snapshot (equity-curve fill). Kite tokens expire
at **6:00 AM IST daily**, so this runs at **6:15 AM IST (00:45 UTC)**.

Without this cron, the owner's token expires each morning and **all live market
data 503s for every user** until someone reconnects Kite by hand.

## One-time setup on the droplet

```bash
ssh root@168.144.90.26

# 1. System Python 3.12 + venv + git (Ubuntu)
apt-get update && apt-get install -y python3.12 python3.12-venv git

# 2. Clone the repo
mkdir -p /opt && git clone https://github.com/kreeshpatel/niftyquant.git /opt/niftyquant
cd /opt/niftyquant

# 3. Venv + the SAME locked backend deps the Fly image uses
python3.12 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install --require-hashes -r dashboard/backend/requirements.lock
```

### Secrets — `dashboard/backend/.env`

Create `/opt/niftyquant/dashboard/backend/.env` (the script calls `load_dotenv()`
from its own directory) and `chmod 600` it:

```
ZERODHA_USER_ID=...
ZERODHA_PASSWORD=...
ZERODHA_TOTP_SECRET=...          # 32-char base32 from 2FA setup, no spaces
KITE_API_KEY=...                 # raw value — NO <> brackets, no quotes
KITE_API_SECRET=...              # raw value — NO <> brackets, no quotes
ENCRYPTION_KEY=...               # MUST be byte-identical to Fly's ENCRYPTION_KEY
DATABASE_URL=...                 # the SAME Supabase session-pooler URL as Fly
```

> **Two values must match Fly exactly or the refresh is useless:**
> - `ENCRYPTION_KEY` — the droplet encrypts the token; the Fly API decrypts it.
>   A different key → Fly can't read the token → 500s.
> - `DATABASE_URL` — must point at the same Supabase DB so the row the droplet
>   writes is the row Fly reads.
>
> The `KITE_API_KEY`/`SECRET` are now sanitized on read (whitespace + `<>`
> stripped), but paste them clean anyway — that `<…>` paste is what broke live
> Kite on 2026-06-26.

```bash
chmod 600 /opt/niftyquant/dashboard/backend/.env
```

### Verify once, by hand

```bash
cd /opt/niftyquant/dashboard/backend
/opt/niftyquant/.venv/bin/python refresh_kite_session.py
# Expect: "access_token received", "Kite session refreshed for admin ...",
# "Expires at <tomorrow> 06:00:00 IST". Then load the dashboard — live data back.
```

### Schedule (crontab, UTC)

```bash
crontab -e
```
Add (00:45 UTC = 06:15 IST, weekdays — markets are closed weekends, and Monday's
run re-arms it before the open):

```cron
45 0 * * 1-5 cd /opt/niftyquant/dashboard/backend && /opt/niftyquant/.venv/bin/python refresh_kite_session.py >> /var/log/kite-refresh.log 2>&1
```

## Keeping it current

- After any push that changes backend deps: `cd /opt/niftyquant && git pull && ./.venv/bin/pip install --require-hashes -r dashboard/backend/requirements.lock`.
- If you rotate the Zerodha password / TOTP / Kite secret / `ENCRYPTION_KEY` /
  DB password, update **both** this `.env` **and** the Fly secrets — they must stay
  in lockstep.
- Tail `/var/log/kite-refresh.log` if live data goes dark in the morning.
