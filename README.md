# Mind IPTV Backend

FastAPI backend (instruction / Crawl4AI hybrid architecture) that serves
Stremio-style addons for the Mind IPTV Flutter app.

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Health check + loaded addon list |
| `GET /api/addons` | All addons with their manifest URLs |
| `GET /api/addon/{id}/manifest.json` | Single addon manifest |
| `POST /api/addon/{id}/{catalog\|meta\|stream}` | Instruction endpoints |
| `POST /api/fetch-result` | Result callback from the Flutter client |
| `GET /admin.html` | Admin panel (password: `ADMIN_PASSWORD` env, else `addon-config.json`) |

## Run locally

```bash
pip install -r requirements.txt
python main.py            # http://localhost:3000  (override with PORT)
```

## Deploy

**Render (free)** — `render.yaml` blueprint is included:

1. Push this repo to GitHub.
2. Render dashboard → **New → Blueprint** → select the repo → **Apply**.
3. Set `ADMIN_PASSWORD` when prompted (optional).

The free instance spins down after ~15 min idle (first request then waits
30-60 s) and has no persistent disk, so admin-panel edits to `addon-config.json`
reset on restart.

A `Dockerfile` is also included for container hosts (Koyeb, Fly.io, Cloud Run,
local Docker).
