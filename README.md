# Paperless-ngx Deployment & Automated Ingestion Tutorial

A multi-container Docker Compose deployment of **Paperless-ngx** on Linux/WSL2, backed by **PostgreSQL 16** and **Valkey 9**, featuring automated OCR ingestion, custom metadata tagging, and local AI audio voiceover generation.

---

## 🏗️ Architecture Overview

Paperless-ngx serves as an open-source digital archive that processes, extracts text via OCR, and indexes incoming documents.

```text
[ Browser / Client ] ──► (Port 8010:8000) ──► [ Paperless Webserver (Granian / Django) ]
                                                       │
                     ┌─────────────────────────────────┴─────────────────────────────────┐
                     ▼                                                                   ▼
       [ PostgreSQL 16 Database ]                                            [ Valkey 9 Task Broker ]
         (Relational Metadata)                                                 (Celery OCR Queues)
```

- **Database:** PostgreSQL 16 handles metadata to avoid SQLite write-lock limits (`db locked`) during parallel ingestion.
- **Message Broker:** Valkey 9 handles asynchronous Celery worker task queues.
- **Security:** Containers communicate across an internal isolated bridge network (`paperlessinternal`).

---

## 🚀 Quickstart & Setup Protocol

### 1. Identify User ID & Group ID
To avoid container permission errors on consumption directories, check your numeric IDs:
```bash
id -u
id -g
```

### 2. Create Storage Directories
```bash
mkdir -p /opt/paperless/{data,media,consume,export}
sudo chown -R 1000:1000 /opt/paperless/consume /opt/paperless/export
chmod -R 775 /opt/paperless/consume /opt/paperless/export
```

### 3. Generate Secret Key
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 4. Deploy Multi-Container Stack
```bash
cd /opt/paperless
docker compose pull
docker compose up -d
```

### 5. Create Administrator Account
```bash
docker compose exec webserver python3 manage.py createsuperuser
```

---

## 📄 Managing Voice Memos & Transcripts

Paperless-ngx processes text, PDFs, and scanned documents. For audio voice notes:

1. Transcribe the audio note (e.g., via Whisper).
2. Save the text transcript as a `.txt` or `.pdf` file (e.g., `voicememo-ai-simulated.txt`).
3. Drop the file into `/opt/paperless/consume/`.
4. Paperless-ngx automatically ingests the file, extracts content, indexes it for full-text search, and applies automated tags (`voice`, `tutorial`, `demo`) and document types (`Transcript`).

---

## 🎙️ Local AI Voiceover Pipeline (Kokoro-82M + FFmpeg)

This repository includes a standalone local TTS pipeline using the open-weight **Kokoro-82M** model and **FFmpeg** to produce broadcast-standard narration tracks for YouTube.

### Audio Pipeline Features
- **Model:** Kokoro-82M (82M parameters, running locally via PyTorch).
- **Voice Blend:** 55% `af_heart` + 45% `af_bella` for natural human female intonation.
- **Audio Mastering:**
  - 90 Hz High-Pass Filter (`highpass=f=90`) to eliminate low-end rumble.
  - 2-Pass EBU R128 Loudness Normalization targeting **-14 LUFS** and **-1.0 dBTP** (YouTube standard).
  - 48 kHz mono broadcast export.

### Generate & Master Audio
```bash
python3 generate_voiceover.py
```

---

## 📊 Verification & Live Testing Checklist

- [x] Multi-container Docker Compose running with PostgreSQL 16 & Valkey 9
- [x] Administrative superuser created via Django CLI
- [x] Document ingestion tested via consumption directory
- [x] Saved views verified: `Tutorial docs` (5 documents) & `Voice docs` (5 documents)
- [x] Full-text search verified: `simulated` query resolving `voicememo-ai-simulated`
- [x] Metadata tagging verified: Tags (`tutorial`, `demo`, `voice`) and Document Type (`Transcript`)
- [x] Local TTS voiceover synthesized and mastered to `-14.7 LUFS` (48 kHz mono)

---

## 🛡️ License
MIT License. Built for self-hosters and developers by [NoCloudNeeded](https://github.com/NoCloudNeeded).

## 🛡️ License
MIT License. Built for self-hosters and developers by [NoCloudNeeded](https://github.com/NoCloudNeeded).
