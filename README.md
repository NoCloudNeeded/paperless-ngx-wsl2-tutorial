# Paperless-ngx on WSL2: Complete Companion Guide

Companion resource for the [NoCloudNeeded](https://github.com/NoCloudNeeded) video tutorial on deploying Paperless-ngx on WSL2 with an isolated Docker Compose stack.

***

## 🏗️ Technical Framing & Architecture

```mermaid
flowchart TD
    Browser["Browser<br/>127.0.0.1:8000"]

    subgraph WSL["WSL2 Host — ~/paperless-ngx-wsl2-tutorial/"]
        Consume["consume/"]
        Export["export/"]
        Data["data/"]
        Media["media/"]
        PGData["pgdata/"]
        RedisData["redisdata/"]
    end

    subgraph Docker["Docker Compose Stack"]
        Web["webserver<br/>Paperless-ngx"]
        DB["db<br/>PostgreSQL 16"]
        Broker["broker<br/>Valkey 9"]
        Internal["paperlessinternal<br/>internal: true"]
    end

    Browser --> Web

    Consume --> Web
    Export --> Web
    Data --> Web
    Media --> Web
    PGData --> DB
    RedisData --> Broker

    Web --> DB
    Web --> Broker

    DB --- Internal
    Broker --- Internal
    Web --- Internal
```

### Architectural Decisions

| Aspect | Project Choice | Rationale |
| :--- | :--- | :--- |
| **Broker** | Valkey 9 (`valkey:9-alpine`) | Open-source Redis-protocol-compatible broker for Celery queues. |
| **Database** | PostgreSQL 16 | Avoids SQLite concurrent write-lock errors during OCR and background processing. |
| **Network** | `paperlessinternal` | Isolated internal Docker network; database and broker expose no host ports. |
| **Port binding** | `127.0.0.1:8000:8000` | Limits the web interface to the local machine. |
| **Storage** | Host bind mounts | Data remains inspectable and portable under `~/paperless-ngx-wsl2-tutorial/`. |
| **Image version** | Pinned release tag | Use a tested official Paperless-ngx release instead of `latest` for reproducible deployments. |

### Document Processing Behavior

- Plain-text files are indexed as searchable text.
- PDFs and scanned images are processed with Tesseract OCR and converted into searchable archive documents.

***

## 📋 1. Prerequisites

Run these checks inside WSL2:

```bash
docker --version
docker compose version
id -u
id -g
```

***

## 📁 2. Host Directory Structure

```bash
mkdir -p ~/paperless-ngx-wsl2-tutorial/{data,media,consume,export,pgdata,redisdata}
cd ~/paperless-ngx-wsl2-tutorial
```

| Directory | Container Path | Purpose |
| :--- | :--- | :--- |
| `data/` | `/usr/src/paperless/data` | Application state, indexes, and classifier models. |
| `media/` | `/usr/src/paperless/media` | Original documents and generated archive media. |
| `consume/` | `/usr/src/paperless/consume` | Folder monitored for new documents. |
| `export/` | `/usr/src/paperless/export` | Destination for `document_exporter` archives. |
| `pgdata/` | `/var/lib/postgresql/data` | PostgreSQL database storage. |
| `redisdata/` | `/data` | Valkey persistence storage. |

***

## ⚙️ 3. Environment Configuration

Generate a secret key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Create `~/paperless-ngx-wsl2-tutorial/.env`:

```env
# WSL2 host user mapping — replace with your own id -u and id -g values
USERMAP_UID=1000
USERMAP_GID=1000

# Paperless-ngx configuration
PAPERLESS_TIME_ZONE=Europe/Brussels
PAPERLESS_SECRET_KEY=REPLACE_WITH_YOUR_GENERATED_64_CHARACTER_KEY
PAPERLESS_OCR_LANGUAGE=eng

# PostgreSQL database
PAPERLESS_DBENGINE=postgresql
PAPERLESS_DBHOST=db
PAPERLESS_DBPORT=5432
PAPERLESS_DBNAME=paperless
PAPERLESS_DBUSER=paperless
PAPERLESS_DBPASS=REPLACE_WITH_A_STRONG_PASSWORD

POSTGRES_DB=paperless
POSTGRES_USER=paperless
POSTGRES_PASSWORD=REPLACE_WITH_A_STRONG_PASSWORD

# Valkey message broker
PAPERLESS_REDIS=redis://broker:6379
```

`PAPERLESS_DBPASS` and `POSTGRES_PASSWORD` must use the same value.

***

## 🐳 4. Docker Compose Configuration

Create `~/paperless-ngx-wsl2-tutorial/docker-compose.yml`:

```yaml
services:
  broker:
    image: docker.io/valkey/valkey:9-alpine
    restart: unless-stopped
    volumes:
      - ./redisdata:/data
    networks:
      - paperlessinternal
    healthcheck:
      test: ["CMD", "valkey-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  db:
    image: docker.io/library/postgres:16
    restart: unless-stopped
    volumes:
      - ./pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-paperless}
      POSTGRES_USER: ${POSTGRES_USER:-paperless}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in .env}
    networks:
      - paperlessinternal
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 10s
      timeout: 5s
      retries: 10

  webserver:
    image: ghcr.io/paperless-ngx/paperless-ngx:3.2.1
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
      broker:
        condition: service_healthy
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - ./data:/usr/src/paperless/data
      - ./media:/usr/src/paperless/media
      - ./consume:/usr/src/paperless/consume
      - ./export:/usr/src/paperless/export
    env_file:
      - .env
    environment:
      PAPERLESS_DBENGINE: ${PAPERLESS_DBENGINE:-postgresql}
      PAPERLESS_DBHOST: ${PAPERLESS_DBHOST:-db}
      PAPERLESS_DBPORT: ${PAPERLESS_DBPORT:-5432}
      PAPERLESS_DBNAME: ${PAPERLESS_DBNAME:-paperless}
      PAPERLESS_DBUSER: ${PAPERLESS_DBUSER:-paperless}
      PAPERLESS_DBPASS: ${PAPERLESS_DBPASS:?Set PAPERLESS_DBPASS in .env}
      PAPERLESS_REDIS: ${PAPERLESS_REDIS:-redis://broker:6379}
      PAPERLESS_SECRET_KEY: ${PAPERLESS_SECRET_KEY:?Set PAPERLESS_SECRET_KEY in .env}
      PAPERLESS_TIME_ZONE: ${PAPERLESS_TIME_ZONE:-America/New_York}
      PAPERLESS_OCR_LANGUAGE: ${PAPERLESS_OCR_LANGUAGE:-eng}
      PAPERLESS_URL: ${PAPERLESS_URL:-http://127.0.0.1:8000}
      USERMAP_UID: ${USERMAP_UID:-1000}
      USERMAP_GID: ${USERMAP_GID:-1000}
    networks:
      - default
      - paperlessinternal

networks:
  default:
  paperlessinternal:
    driver: bridge
    internal: true
```

***

## 🚀 5. Launch & Verification

```bash
docker compose pull
docker compose up -d
docker compose ps
```

Create an administrator account:

```bash
docker compose exec webserver createsuperuser
```

Check the database and broker:

```bash
docker compose exec db pg_isready -U paperless
docker compose exec broker valkey-cli ping
```

Open:

```text
http://127.0.0.1:8000
```

***

## 🔍 6. Test Document Ingestion

1. Sign in to Paperless-ngx.
2. Place a PDF or scanned document in `~/paperless-ngx-wsl2-tutorial/consume/`.
3. Wait for Paperless-ngx to process it.
4. Open the document and confirm:
   - OCR text is searchable.
   - Tags, correspondent, document type, and storage path can be assigned.
   - Full-text search returns the document.

For automated organization, create workflows in **Manage → Workflows**. For example, assign a tag when a filename contains a chosen pattern.

***

## 💾 7. Backup & Restore Protocol

### Export documents and metadata

```bash
docker compose exec -T webserver document_exporter /usr/src/paperless/export
```

### Create a PostgreSQL logical backup

```bash
docker compose exec -T db pg_dump -U paperless paperless > ~/paperless-exports/paperless-db-$(date +%F).sql
```

Protect the export directory, database dump, `.env`, and Compose configuration. Copy backups to separate storage; the local `export/` directory is a staging location, not a complete offsite backup.

### Test restoration

On a clean Paperless-ngx instance running the **same major version**:

```bash
docker compose exec -T webserver document_importer /usr/src/paperless/export
```

Verify that documents, metadata, tags, users, and search results were restored. A backup is only proven once it has been restored successfully.

***

## 🧾 8. Demo: Automated Invoice Intake

This demo turns one fake invoice into a searchable, tagged and filed document with no clicks. Use fake data only.

### Create the demo invoice

```bash
pip install reportlab
python3 - <<'EOF'
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
c = canvas.Canvas("demo-energy-invoice-2026-09.pdf", pagesize=A4)
c.setFont("Helvetica-Bold", 22); c.drawString(72, 760, "Demo Energy Ltd.")
c.setFont("Helvetica-Bold", 16); c.drawString(72, 720, "Electricity Invoice")
c.setFont("Helvetica", 14)
for i, t in enumerate(["Invoice Number: DEMO-2026-091", "Amount Due: 79.99 EUR", "Due Date: 2026-10-15", "VAT included (21%)"]):
    c.drawString(72, 680 - i*28, t)
c.save()
EOF
```

### Matching rules

Create these in **Manage → Attributes**. Set any old demo items to **None** so they do not tag unrelated documents.

| Type | Name | Algorithm | Match |
| --- | --- | --- | --- |
| Correspondent | Demo Energy Ltd | Exact match | `Demo Energy Ltd` |
| Document type | Invoice | Exact match | `Electricity Invoice` |
| Tag | Action Required | Exact match | `Amount Due` |
| Tag | Tax | Any word | `VAT Tax` |
| Tag | Finance | None | assigned by the workflow |
| Tag | YouTube Demo | None | assigned by the workflow |

### Storage path

Name: `Finance Invoices`. Algorithm: Exact match on `Demo Energy Ltd`.

```text
Finance/{{ created_year }}/{{ correspondent }}/{{ document_type }}/{{ title }}
```

### Workflow

Create it in **Manage → Workflows**. Name: `Demo invoice intake`. Sort order: `1`.

- Trigger: **Document Added**, filename filter `*energy*`
- Action: **Assignment**, assign tags `Finance` and `YouTube Demo`

### Test

```bash
cp demo-energy-invoice-2026-09.pdf consume/
```

Expected result: correspondent Demo Energy Ltd, type Invoice, tags Action Required, Tax, Finance and YouTube Demo, storage path Finance Invoices. Search `DEMO-2026-091` to confirm OCR and indexing.

---

## 📚 Repository Files

- `README.md` — this guide.
- `docker-compose.yml` — Paperless-ngx, PostgreSQL, and Valkey stack.
- `.env.example` — environment-variable template.
- `LICENSE` — MIT license.
