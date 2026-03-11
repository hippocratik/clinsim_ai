# Deployment Guide — VM Server (Linux)

This guide covers deploying ClinSim AI on a single Linux VM (e.g. Ubuntu 22.04 on AWS EC2, DigitalOcean Droplet, or GCP Compute Engine).

The deployment is two phases:
1. **Build** — run the data pipeline once on the server to produce `data/` artifacts
2. **Run** — start the backend with Uvicorn behind Nginx, serve the frontend as a static Next.js export or via a Node process

---

## Table of Contents

- [Recommended Server Specs](#recommended-server-specs)
- [Prerequisites](#prerequisites)
- [Step 1 — Server Setup](#step-1--server-setup)
- [Step 2 — Clone and Install](#step-2--clone-and-install)
- [Step 3 — Configure Environment](#step-3--configure-environment)
- [Step 4 — Build Data Artifacts](#step-4--build-data-artifacts)
- [Step 5 — Start the Backend](#step-5--start-the-backend)
- [Step 6 — Deploy the Frontend](#step-6--deploy-the-frontend)
- [Step 7 — Configure Nginx](#step-7--configure-nginx)
- [Step 8 — Systemd Services](#step-8--systemd-services)
- [Health Check](#health-check)
- [Updating the Application](#updating-the-application)
- [Rebuilding Data Artifacts](#rebuilding-data-artifacts)
- [Backup](#backup)
- [Troubleshooting](#troubleshooting)

---

## Recommended Server Specs

| Component | Minimum | Recommended |
|---|---|---|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB |
| Disk | 20 GB | 50 GB |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

**RAM note:** Loading the FAISS index and sentence-transformers model at startup requires ~1–2 GB RAM. With 2000 cases, the `cases.json` and `chunks.json` files add another ~500 MB. 4 GB is the practical minimum; 8 GB is comfortable.

**Disk note:** The HuggingFace dataset download cache is ~2–3 GB. The generated `data/` artifacts are ~100–500 MB depending on case count. Allow at least 10 GB free before running the pipeline.

---

## Prerequisites

On your local machine:
- SSH access to the server
- The server's public IP or domain name

---

## Step 1 — Server Setup

SSH into the server and install system dependencies:

```bash
sudo apt update && sudo apt upgrade -y

# Python build tools
sudo apt install -y python3.11 python3.11-venv python3-pip build-essential

# Node.js 20 (for frontend)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Nginx (reverse proxy)
sudo apt install -y nginx

# Git
sudo apt install -y git

# uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env   # add uv to PATH for current session
```

Add `uv` to PATH permanently:

```bash
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

---

## Step 2 — Clone and Install

```bash
cd /opt
sudo git clone https://github.com/hippocratik/clinsim_ai.git
sudo chown -R $USER:$USER /opt/clinsim_ai
cd /opt/clinsim_ai

# Install backend dependencies
cd backend
uv sync --all-extras

# Install frontend dependencies
cd ../frontend
npm install
```

---

## Step 3 — Configure Environment

### Backend

```bash
cd /opt/clinsim_ai/backend
cp .env.example .env
nano .env
```

Set at minimum:

```ini
ANTHROPIC_API_KEY=sk-ant-your-key-here
LLM_PROVIDER=anthropic

# Update CORS to match your domain
CORS_ORIGINS=https://yourdomain.com,http://yourdomain.com
```

Restrict file permissions so the API key is not world-readable:

```bash
chmod 600 /opt/clinsim_ai/backend/.env
```

### Frontend

```bash
cd /opt/clinsim_ai/frontend
cat > .env.local << 'EOF'
NEXT_PUBLIC_API_MODE=real
NEXT_PUBLIC_API_URL=https://yourdomain.com
EOF
```

Replace `https://yourdomain.com` with your actual domain or server IP. If you don't have a domain yet, use `http://<server-ip>:8000` temporarily.

---

## Step 4 — Build Data Artifacts

This is the most time-consuming step. Run it inside a `tmux` or `screen` session so it continues if your SSH connection drops.

```bash
# Start a tmux session
tmux new -s foundation

cd /opt/clinsim_ai/backend

# Build with desired number of cases
# Start with 50 to verify everything works, then run again for more
uv run python -m app.cli.build_foundation --num-cases 50
```

Expected output:

```
============================================================
ClinSim AI Foundation Builder
============================================================

[1/5] Loading MIMIC dataset from HuggingFace...
  Loaded 45,000 clinical cases
[2/5] Selecting 50 cases to process...
[3/5] Parsing discharge summaries with Claude...
  Processing case 1/50 (hadm_id: 123456)...
    ✓ Parsed: Chest pain and shortness of breath...
  ...
[4/5] Building RAG index...
  Created 350 chunks from 50 cases
  Built FAISS index with 350 vectors
[5/5] Saving artifacts...
  ✓ Saved data/cases.json
  ✓ Saved data/chunks.json
  ✓ Saved data/faiss.index
```

When done, detach from tmux with `Ctrl+B D`. To check on it later: `tmux attach -t foundation`.

**Verify artifacts were created:**

```bash
ls -lh /opt/clinsim_ai/backend/data/
# Should show cases.json, chunks.json, faiss.index, mock_session.json
```

---

## Step 5 — Start the Backend

Test that the backend starts correctly before setting up systemd:

```bash
cd /opt/clinsim_ai/backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Check the startup output:

```
Starting ClinSim AI backend...
  ✓ Loaded 50 cases from data/cases.json
  ✓ Loaded 45 ICD-9 codes from cases
  ✓ Loaded 350 chunks from data/chunks.json
  ✓ RAG service ready (index: data/faiss.index)
  ✓ Session manager ready
  ✓ Scoring engine ready
  ✓ LLM service ready
ClinSim AI backend started.
```

If you see warnings about RAG or LLM being unavailable, check your `.env` configuration.

Hit `Ctrl+C` to stop — systemd will manage it in production.

> **Important:** Always use `--workers 1`. The in-memory session store and generation jobs are not shared across multiple Uvicorn workers.

---

## Step 6 — Deploy the Frontend

Build the Next.js app for production:

```bash
cd /opt/clinsim_ai/frontend
npm run build
```

This produces `.next/` — the production-ready Next.js build. The frontend will be served by a Node.js process via `npm start`.

Test it:

```bash
npm start
# Frontend at http://localhost:3000
```

Hit `Ctrl+C` — systemd will manage this in production.

---

## Step 7 — Configure Nginx

Nginx acts as the reverse proxy, routing `/api/*` and `/health` to the FastAPI backend (port 8000) and everything else to the Next.js frontend (port 3000).

```bash
sudo nano /etc/nginx/sites-available/clinsim
```

Paste the following (replace `yourdomain.com` or use `_` for IP-only access):

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Backend API + health
    location ~ ^/(api|health)(/|$) {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE support (patient chat streaming)
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 120s;
        chunked_transfer_encoding on;
    }

    # Frontend
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site and reload Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/clinsim /etc/nginx/sites-enabled/
sudo nginx -t          # test config
sudo systemctl reload nginx
```

**Optional — HTTPS with Let's Encrypt:**

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
# Follow prompts — certbot will update the Nginx config automatically
```

---

## Step 8 — Systemd Services

Create systemd services so the backend and frontend start automatically on boot and restart on failure.

### Backend service

```bash
sudo nano /etc/systemd/system/clinsim-backend.service
```

```ini
[Unit]
Description=ClinSim AI Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/clinsim_ai/backend
ExecStart=/home/ubuntu/.cargo/bin/uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

> Replace `ubuntu` with your actual Linux username. Check the `uv` path with `which uv`.

### Frontend service

```bash
sudo nano /etc/systemd/system/clinsim-frontend.service
```

```ini
[Unit]
Description=ClinSim AI Frontend
After=network.target clinsim-backend.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/clinsim_ai/frontend
ExecStart=/usr/bin/npm start
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Enable and start both services

```bash
sudo systemctl daemon-reload
sudo systemctl enable clinsim-backend clinsim-frontend
sudo systemctl start clinsim-backend clinsim-frontend

# Check status
sudo systemctl status clinsim-backend
sudo systemctl status clinsim-frontend
```

---

## Health Check

Verify everything is running end-to-end:

```bash
# Backend health
curl http://localhost:8000/health

# Expected:
# {"status":"ok","timestamp":"...","services":{"rag":"ok","llm":"ok","cases_loaded":50}}

# Through Nginx
curl http://yourdomain.com/health

# Cases endpoint
curl http://yourdomain.com/api/cases
```

If `status` is `"degraded"`, check the logs:

```bash
sudo journalctl -u clinsim-backend -n 50
```

---

## Updating the Application

To deploy a new version:

```bash
cd /opt/clinsim_ai

# Pull latest code
git pull origin main

# Update backend dependencies if changed
cd backend && uv sync --all-extras

# Rebuild frontend
cd ../frontend && npm install && npm run build

# Restart services
sudo systemctl restart clinsim-backend clinsim-frontend
```

---

## Rebuilding Data Artifacts

Run the pipeline again whenever you want more cases or the dataset is updated. Existing `cases.json` will be overwritten.

```bash
tmux new -s rebuild
cd /opt/clinsim_ai/backend

# Append to existing cases instead of overwriting:
uv run python -m app.cli.generate_cases \
  --source-case case_001 \
  --count 10 \
  --append

# Or rebuild from scratch with more cases:
uv run python -m app.cli.build_foundation --num-cases 200

# Restart backend to pick up new artifacts
sudo systemctl restart clinsim-backend
```

---

## Backup

The `data/` directory is gitignored and contains the only copy of your processed cases and FAISS index. Back it up regularly:

```bash
# Manual backup to a local tar
cd /opt/clinsim_ai/backend
tar -czf ~/clinsim-data-$(date +%Y%m%d).tar.gz data/

# Copy to your local machine
scp ubuntu@yourdomain.com:~/clinsim-data-*.tar.gz ./backups/
```

For automated backups, consider a daily cron job that copies `data/` to an S3 bucket or equivalent object storage.

---

## Troubleshooting

### Backend fails to start — "RAG disabled"

```
⚠ FAISS index not found at data/faiss.index — RAG disabled
```

The data pipeline has not been run or the `data/` directory is in the wrong location. Ensure you run `build_foundation` from inside `backend/` and that `data/faiss.index` exists relative to where you start Uvicorn.

### WinError 1114 / torch import failure (Windows only)

On Windows, `sentence-transformers` may fail to import due to a DLL load error. The backend will start with RAG disabled — chat will work with reduced context quality. To fix, install the CPU-only torch build manually:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Frontend shows "Could not load cases"

- Verify the backend is running: `curl http://localhost:8000/health`
- Check that `NEXT_PUBLIC_API_MODE=real` and `NEXT_PUBLIC_API_URL` are set correctly in `frontend/.env.local`
- After changing `.env.local`, rebuild the frontend: `npm run build && sudo systemctl restart clinsim-frontend`

### SSE chat not streaming

Check the Nginx config — `proxy_buffering off` is required for SSE to work through the reverse proxy. If missing, the entire response is buffered and only appears when the LLM finishes.

### Session state lost after backend restart

This is expected — session state is in-memory only. Active training sessions will be lost on restart. Schedule restarts during off-hours.

### High memory usage

With 2000 cases, expect ~2–3 GB RAM usage at steady state (FAISS index + sentence-transformers model + case data). If the process is killed by the OOM killer, upgrade to a larger instance or reduce the number of cases.

### Logs

```bash
# Backend logs
sudo journalctl -u clinsim-backend -f

# Frontend logs
sudo journalctl -u clinsim-frontend -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log
```
