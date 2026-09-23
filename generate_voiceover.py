import subprocess
import re
import json
import soundfile as sf
import numpy as np
from kokoro import KPipeline

SAMPLE_RATE = 24000
pipeline = KPipeline(lang_code='a')

# Load and blend voices (55% af_heart + 45% af_bella)
v_heart = pipeline.load_voice('af_heart')
v_bella = pipeline.load_voice('af_bella')
blended_voice = 0.55 * v_heart + 0.45 * v_bella

# Video narration — audience-focused only; no personal workflow details
text = """Paperless-ngx transforms physical documents into a searchable personal archive.

By pairing it with PostgreSQL and Valkey in Docker Compose, you avoid database locking issues during heavy O-C-R ingestion.

Drop a PDF into the consume folder, and Paperless-ngx processes it automatically.

For scanned documents, it runs O-C-R, extracts the text, and creates a searchable archive copy.

Then search for any word inside your documents, assign tags and document types, and organize everything with saved views.

In the next video, we will configure automated workflows so Paperless-ngx organizes new documents without manual work."""

print('[1/3] Synthesizing speech with Kokoro-82M...')
chunks = list(pipeline(text, voice=blended_voice, speed=0.92, split_pattern=r'\n+'))
audio_segments = []

for i, (gs, ps, audio) in enumerate(chunks):
    audio_segments.append(audio)
    if i < len(chunks) - 1:
        # 0.55s natural breathing pause between distinct paragraphs
        audio_segments.append(np.zeros(int(SAMPLE_RATE * 0.55), dtype=np.float32))

# 0.4s clean trailing silence
audio_segments.append(np.zeros(int(SAMPLE_RATE * 0.4), dtype=np.float32))
raw_audio = np.concatenate(audio_segments)
sf.write('raw_tts.wav', raw_audio, SAMPLE_RATE)

print('[2/3] Mastering audio with FFmpeg (90Hz High-Pass + 2-Pass -14 LUFS Loudnorm)...')

# --- PASS 1: Measure loudness ---
cmd_pass1 = [
    'ffmpeg', '-y', '-i', 'raw_tts.wav',
    '-af', 'highpass=f=90,loudnorm=I=-14:TP=-1.0:LRA=7:print_format=json',
    '-f', 'null', '-'
]
res = subprocess.run(cmd_pass1, capture_output=True, text=True)
m = re.search(r'\{[\s\S]*\}', res.stderr)
stats = json.loads(m.group(0))

measured_lra = float(stats['input_lra'])
if abs(measured_lra - 7) > 10:
    print(f"  Warning: measured LRA ({measured_lra}) deviates from target (7) — verify loudness output.")

# --- PASS 2: Apply linear normalization & 48kHz upsampling ---
cmd_pass2 = [
    'ffmpeg', '-y', '-i', 'raw_tts.wav',
    '-af', (
        f'highpass=f=90,'
        f'loudnorm=I=-14:TP=-1.0:LRA=7:'
        f'measured_I={stats["input_i"]}:'
        f'measured_TP={stats["input_tp"]}:'
        f'measured_LRA={stats["input_lra"]}:'
        f'measured_thresh={stats["input_thresh"]}:'
        f'offset={stats["target_offset"]}:'
        f'linear=true'
    ),
    '-ar', '48000',
    '-ac', '1',
    'paperless_mastered_youtube.wav'
]
subprocess.run(cmd_pass2, check=True)

# --- Verification Check ---
print('[3/3] Mastered track saved: paperless_mastered_youtube.wav (48kHz mono, -14 LUFS, -1.0 dBTP)')
cmd_check = ['ffmpeg', '-i', 'paperless_mastered_youtube.wav', '-af', 'ebur128=framelog=verbose', '-f', 'null', '-']
check_res = subprocess.run(cmd_check, capture_output=True, text=True)
for line in check_res.stderr.split('\n'):
    if 'I:' in line and 'LUFS' in line:
        print(f'      Verified {line.strip()}')
        break
