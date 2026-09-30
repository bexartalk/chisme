"""Build Lotería Chismosa's recorded calls: static/loteria/audio/NN.mp3 (card 1-54: its verse, then its name) plus
intro.mp3 ("¡Se va y se corre con…!"), loteria.mp3 ("¡Lotería!") and over.mp3 ("¡Se acabaron las cartas!").

Voice: Piper TTS (https://github.com/OHF-Voice/piper1-gpl) with the es_MX "claude" high-quality voice
(https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_MX/claude/high, MODEL_CARD: license apache-2.0).
Everything runs offline on this machine; the app only ships the finished mp3 files.

    python3 -m venv /tmp/tts && /tmp/tts/bin/pip install piper-tts
    PIPER=/tmp/tts/bin/piper VOICE=/path/es_MX-claude-high.onnx python3 tools/make_loteria_audio.py
Needs node (reads static/loteria_cards.js) and ffmpeg."""
import json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "static", "loteria", "audio")
PIPER = os.environ.get("PIPER", "/workspace/scratch/tts/venv/bin/piper")
VOICE = os.environ.get("VOICE", "/workspace/scratch/tts/es_MX-claude-high.onnx")
JS = "const L = require(process.argv[1]); console.log(JSON.stringify({ cards: L.CARDS.map((c) => [c.id, L.callText(c)]), lines: L.LINES_ES }))"

def spoken(t):   # what the voice reads: no ellipsis character, pa' → pa
    return re.sub(r"\s+", " ", t.replace("…", ",").replace("pa'", "pa").replace(",!", "!")).strip()

def make(key, text, tmp):
    wav = os.path.join(tmp, key + ".wav")
    subprocess.run([PIPER, "-m", VOICE, "-f", wav, "--length-scale", "1.08", "--sentence-silence", "0.35"], input=spoken(text).encode(), check=True, capture_output=True)
    mp3 = os.path.join(OUT, key + ".mp3")
    # trim the silence at both ends, a touch of warmth, loudness-normalized, mono 44 kbps
    af = "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,loudnorm=I=-16:TP=-1.5:LRA=11"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-af", af, "-ac", "1", "-ar", "22050", "-b:a", "44k", mp3], check=True)
    return mp3

def main():
    os.makedirs(OUT, exist_ok=True)
    data = json.loads(subprocess.run(["node", "-e", JS, os.path.join(HERE, "static", "loteria_cards.js")], capture_output=True, text=True, check=True).stdout)
    jobs = [(f"{i:02d}", t) for i, t in data["cards"]] + [(k, v) for k, v in data["lines"].items()]
    only = set(sys.argv[1:])
    with tempfile.TemporaryDirectory() as tmp:
        for key, text in jobs:
            if only and key not in only: continue
            make(key, text, tmp); print(key, spoken(text))
    print(len(jobs), "clips in", OUT)

if __name__ == "__main__":
    main()
