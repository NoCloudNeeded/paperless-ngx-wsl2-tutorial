import subprocess, re, json
import soundfile as sf
import numpy as np
from kokoro import KPipeline

pipeline = KPipeline(lang_code='a')

# Load and blend voices (0.55 heart + 0.45 bella)
v_heart = pipeline.load_voice('af_heart')
v_bella = pipeline.load_voice('af_bella')
blended_voice = 0.55 * v_heart + 0.45 * v_bella

text = """Paperless-ngx transforms physical documents into a searchable personal archive.

By pairing it with PostgreSQL and Valkey in Docker Compose, you eliminate database locking issues during heavy O-C-R ingestion.

Let us look at our saved views for Tutorial docs and Voice docs, run a search for simulated transcripts, and inspect the automated tags."""

chunks = list(pipeline(text, voice=blended_voice, speed=0.92, split_pattern=r'\n+'))
audio_segments = []

for i, (gs, ps, audio) in enumerate(chunks):
    audio_segments.append(audio)
    if i < len(chunks) - 1:
        audio_segments.append(np.zeros(int(24000 * 0.55)))

audio_segments.append(np.zeros(int(24000 * 0.4)))
raw_audio = np.concatenate(audio_segments)
sf.write('raw_tts.wav', raw_audio, 24000)

print('[1/2] TTS Synthesis Complete. Mastering with FFmpeg (90Hz Highpass + -14 LUFS Loudnorm)...')

cmd_pass1 = [
    'ffmpeg', '-y', '-i', 'raw_tts.wav',
    '-af', 'highpass=f=90,loudnorm=I=-14:TP=-1.0:LRA=7:print_format=json',
    '-f', 'null', '-'
]
res = subprocess.run(cmd_pass1, capture_output=True, text=True)
m = re.search(r'\{[\s\S]*\}', res.stderr)
stats = json.loads(m.group(0))

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
print('[2/2] Mastered track ready: paperless_mastered_youtube.wav (-14 LUFS, 48kHz mono)')
