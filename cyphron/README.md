## Cyphron (Fraud Detection System) — Foundation Setup

This repository is **structure-only** for a full-stack fraud detection system.

- **No business logic yet**
- Minimal runnable services with simple startup prints/logs

### Repo layout

- `simulator/`: Generates dummy transactions (prints to console)
- `pipeline/`: FastAPI backend skeleton + placeholder clients
- `ml_training/`: Training scaffolding (placeholder scripts)
- `dashboard/`: Next.js dashboard skeleton
- `infra/`: Infra setup scripts (placeholders)
- `docs/`: Architecture + API references (placeholders)

### Quick start (local)

#### 1) Environment

Copy env template and fill values as needed:

- `cyphron/.env.example` → create your own `.env` (not committed)

#### 2) Redis (Docker)

From `cyphron/`:

```bash
docker compose up -d redis
```

#### 3) Simulator

```bash
cd simulator
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python main.py
```

You should see:

- `Simulator started`
- A printed dummy transaction dict/json

#### 4) Backend (FastAPI)

```bash
cd pipeline
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python main.py
```

Then open `http://localhost:8001/` (or your `PIPELINE_PORT`) and you should get:

- `"Cyphron backend running"`

#### 5) Dashboard (Next.js)

```bash
cd dashboard
npm install
npm run dev
```

Open `http://localhost:3000/` and you should see:

- `Cyphron Dashboard Running`
- Browser console log: `Frontend running`

### Port conflicts (Windows)

If a port is already in use, you can free it:

```powershell
# free backend port
$p=(Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess); if($p){Stop-Process -Id $p -Force}

# free dashboard port
$p=(Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess); if($p){Stop-Process -Id $p -Force}
```

Or run the dashboard on another port:

```bash
npm run dev:3001
```

