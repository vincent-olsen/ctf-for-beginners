#!/usr/bin/env python3
"""Rebuild platform/theme/first-blood.mp3, the voice that says "FIRST BLOOD".

The committed file is what the Scoreboard plays (platform/theme/first-blood.js),
so this is only for changing the voice. Any short mp3 of your own works just as
well: a friend with a deep voice, say. Replace the file, keep the name, and
set VOICE_BEATS at the top of first-blood.js to where its two words start.

What this does: the Kokoro text-to-speech model (Apache 2.0, voice "am_onyx")
says "First. Blood.", and the take is then made into a machine's idea of an arena
announcer. Three copies of it, in step: the body, pitched far down; the highs of
a copy pitched down only a little, which keep the consonants crisp; and a copy
an octave below the body. Then a bass lift, a little bit-crushed grit, hard
compression, a hall reverb, and the end of "blood" caught in a loop that breaks
up as it fades. It runs offline and needs ffmpeg (with rubberband) on the PATH and

    pip install sherpa-onnx onnx numpy soundfile
    curl -LO https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_0.tar.bz2
    tar xjf kokoro-multi-lang-v1_0.tar.bz2

    tools/first-blood-voice.py kokoro-multi-lang-v1_0

It prints where the two words start, for VOICE_BEATS.
"""

import os
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf

TEXT = "First. Blood."
VOICE = "am_onyx"  # the deepest of Kokoro's English voices
SPEED = 0.85
TEMPO = 0.87  # slower: more weight on each word
BODY = 0.70  # the deep layer's pitch, of the original's
THROAT = 0.88  # how much of that also lowers the formants (a bigger chest), the rest is pitch alone
CLARITY = 0.88  # the pitch of the layer whose highs keep the words clear
RATE = 48000
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "platform", "theme", "first-blood.mp3")


def speak(model_dir, path):
    import sherpa_onnx

    d = model_dir
    tts = sherpa_onnx.OfflineTts(
        sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
                    model=f"{d}/model.onnx",
                    voices=f"{d}/voices.bin",
                    tokens=f"{d}/tokens.txt",
                    data_dir=f"{d}/espeak-ng-data",
                    dict_dir=f"{d}/dict",
                    lexicon=f"{d}/lexicon-us-en.txt,{d}/lexicon-gb-en.txt",
                ),
                num_threads=2,
                provider="cpu",
            ),
            max_num_sentences=1,
        )
    )
    # The voice's place in the model's own table.
    import onnx

    meta = {p.key: p.value for p in onnx.load(f"{d}/model.onnx", load_external_data=False).metadata_props}
    sid = meta["speaker_names"].split(",").index(VOICE)
    audio = tts.generate(TEXT, sid=sid, speed=SPEED)
    sf.write(path, np.array(audio.samples, dtype=np.float32), audio.sample_rate)


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def deepen(src, dst):
    """The three layers, a bass lift, grit and compression: dry and mono."""
    stretch = f"tempo={TEMPO}:pitchq=quality"
    ffmpeg(
        "-i", src, "-filter_complex",
        f"[0:a]aresample={RATE},apad=pad_dur=0.15,asplit=3[a][b][c];"
        # the body: formants and pitch down together a little, then pitch alone the rest of the way
        f"[a]rubberband=pitch={THROAT}:{stretch}:formant=shifted,"
        f"rubberband=pitch={BODY / THROAT}:formant=preserved:pitchq=quality,lowpass=f=2600,asplit=2[body][crush];"
        # grit: the body through a bit crusher, mixed in low
        "[crush]acrusher=bits=6:samples=8:mix=1:aa=0.3,highpass=f=300,lowpass=f=3500,volume=0.16[grit];"
        # clarity: only the highs of a copy that is barely lowered
        f"[b]rubberband=pitch={CLARITY}:{stretch}:formant=shifted,highpass=f=1500,highpass=f=1500,volume=-5dB[clear];"
        # an octave under the body
        f"[c]rubberband=pitch={BODY / 2}:{stretch}:formant=shifted,lowpass=f=420,volume=-6dB[sub];"
        "[body][grit][clear][sub]amix=inputs=4:normalize=0:duration=longest,"
        "highpass=f=32,"
        "equalizer=f=85:t=q:w=0.8:g=7,"
        "equalizer=f=300:t=q:w=1.0:g=-2.5,"
        "equalizer=f=3000:t=q:w=1.1:g=3,"
        "lowpass=f=9500,"
        "acompressor=threshold=-22dB:ratio=5:attack=3:release=140:makeup=5,"
        "asoftclip=type=tanh:threshold=0.85",
        "-ac", "1", dst,
    )  # fmt: skip


def hall(seconds=2.2, rt60=1.7):
    """A hall's impulse response: a pre-delay, four early reflections and a dark,
    decaying stereo noise tail."""
    rng = np.random.default_rng(7)
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    noise = rng.standard_normal((n, 2)) * np.exp(-t * 6.91 / rt60)[:, None]
    tail = np.zeros_like(noise)
    state = np.zeros(2)
    for i in range(n):  # a lowpass that closes as the tail fades: the highs die first
        a = 0.25 + 0.6 * min(1.0, t[i] / 1.2)
        state = a * state + (1 - a) * noise[i]
        tail[i] = state
    pre = int(0.022 * RATE)
    ir = np.zeros((n + pre, 2))
    ir[pre:] = tail * 0.5
    for delay, gain, pan in ((0.011, 0.5, 0.3), (0.019, 0.4, 0.8), (0.031, 0.32, 0.1), (0.047, 0.25, 0.65)):
        k = int(delay * RATE)
        ir[k, 0] += gain * (1 - pan)
        ir[k, 1] += gain * pan
    return ir


def onsets(x, rate):
    """Where each of the two words starts, in seconds: the first loud point, and
    the first loud point after the quietest one in the middle."""
    w = int(0.02 * rate)
    env = np.sqrt(np.convolve(x**2, np.ones(w) / w, "same"))
    loud = np.where(env > 0.3 * env.max())[0]
    first = loud[0]
    a, b = first + int(0.2 * rate), first + int(0.7 * rate)
    gap = a + int(np.argmin(env[a:b]))
    second = gap + np.where(env[gap:] > 0.3 * env.max())[0][0]
    return first / rate, gap / rate, second / rate


def crush(x, hold, bits):
    """Fewer samples (each held `hold` long) and fewer bits: the sound of bad data."""
    held = np.repeat(x[::hold], hold)[: len(x)]
    steps = 2 ** (bits - 1)
    return np.round(held * steps) / steps


def stutter(dry, rate):
    """The end of "blood" caught in a loop, like a skipping disc: its last slice
    again and again, quieter and more broken each time, from side to side."""
    w = int(0.02 * rate)
    env = np.sqrt(np.convolve(dry**2, np.ones(w) / w, "same"))
    last = np.where(env > 0.25 * env.max())[0][-1]  # where the word ends
    size, fade = int(0.095 * rate), int(0.006 * rate)
    piece = dry[last - size : last].copy()  # its last tenth of a second, the "d" included
    piece[:fade] *= np.linspace(0, 1, fade)
    piece[-fade:] *= np.linspace(1, 0, fade)
    out = np.zeros((len(dry) + int(1.2 * rate), 2))
    for i, (hold, bits) in enumerate(((2, 8), (3, 7), (5, 6), (8, 5), (12, 5), (18, 4), (26, 4))):
        k = last + int(0.02 * rate) + i * int(0.105 * rate)  # after the word, never over it
        tap = crush(piece, hold, bits) * 0.7 * 0.74**i
        pan = 0.25 if i % 2 else 0.75
        out[k : k + size, 0] += tap * (1 - pan) * 2
        out[k : k + size, 1] += tap * pan * 2
    return out


def reverb(src, dst, wet_db=-13.0):
    dry, rate = sf.read(src, dtype="float64")
    assert rate == RATE and dry.ndim == 1
    ir = hall()
    n = len(dry) + len(ir) - 1
    size = 1 << (n - 1).bit_length()
    spectrum = np.fft.rfft(dry, size)
    wet = np.stack([np.fft.irfft(spectrum * np.fft.rfft(ir[:, c], size), size)[:n] for c in (0, 1)], axis=1)
    # The tail's level against the voice's, by loudness, not by the IR's scale.
    wet *= 10 ** (wet_db / 20) * np.sqrt(np.mean(dry**2)) / np.sqrt(np.mean(wet[: len(dry)] ** 2))
    out = wet
    out[: len(dry)] += dry[:, None]
    again = stutter(dry, rate)
    m = min(len(out), len(again))
    out[:m] += again[:m]
    sf.write(dst, out.astype(np.float32), RATE)


def finish(src, dst):
    ffmpeg(
        "-i", src, "-af",
        "volume=5dB,alimiter=limit=0.89:level=false:attack=2:release=60,"
        "afade=t=out:st=2.7:d=0.7,atrim=end=3.4",
        "-ar", "44100", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "112k", "-map_metadata", "-1", dst,
    )  # fmt: skip


def beats(path):
    """Where each of the two words starts, in seconds, in the file as a browser decodes it."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
        capture_output=True, check=True,
    ).stdout  # fmt: skip
    first, _, second = onsets(np.frombuffer(raw, dtype=np.float32).astype(np.float64), 16000)
    return first, second


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    with tempfile.TemporaryDirectory() as tmp:
        take, deep, wet = (os.path.join(tmp, n) for n in ("take.wav", "deep.wav", "wet.wav"))
        speak(sys.argv[1], take)
        deepen(take, deep)
        reverb(deep, wet)
        finish(wet, OUT)
    first, second = beats(OUT)
    print(f"wrote {os.path.normpath(OUT)} ({os.path.getsize(OUT)} bytes)")
    print(f"VOICE_BEATS = [{first:.2f}, {second:.2f}]")


if __name__ == "__main__":
    main()
