#!/usr/bin/env python3
"""Render the OS1 boot chime (the "Her" frequency sweep) to a WAV file.

Headless — no GUI, no audio device. Reuses the synth math from
python_loading/os1_bootup.py so the shipped boot sound matches the synth.

Usage:
    python scripts/render-boot-sound.py [out.wav]
"""
import sys
import numpy as np
import scipy.signal as signal
from scipy.io import wavfile

SAMPLE_RATE = 44100
FREQ_START = 180.0
FREQ_END = 1100.0
HARMONICS = [(1.00, 1.00), (0.45, 2.00), (0.20, 3.00), (0.08, 4.00), (0.04, 5.02)]


def full_sweep(duration: float = 3.4) -> np.ndarray:
    n = int(SAMPLE_RATE * duration)
    freq_t = np.linspace(FREQ_START, FREQ_END, n)
    phase = 2 * np.pi * np.cumsum(freq_t) / SAMPLE_RATE

    wave = np.zeros(n)
    for amp, mult in HARMONICS:
        wave += amp * np.sin(phase * mult)
    wave /= np.max(np.abs(wave)) + 1e-9

    attack = int(0.20 * SAMPLE_RATE)
    release = int(0.45 * SAMPLE_RATE)
    env = np.ones(n)
    env[:attack] = np.linspace(0, 1, attack)
    env[-release:] = np.linspace(1, 0, release)

    # Dynamic low-pass that opens up as the sweep rises.
    out = np.empty_like(wave)
    chunk = 512
    for i in range(0, n, chunk):
        sl = slice(i, min(i + chunk, n))
        fc = float(np.mean(freq_t[sl]))
        cut = min(fc * 2.2, 18000) / (SAMPLE_RATE / 2)
        b, a = signal.butter(2, cut, btype="low")
        out[sl] = signal.lfilter(b, a, wave[sl])

    out *= env * 0.85
    return out.astype(np.float32)


def main() -> None:
    out_path = sys.argv[1] if len(sys.argv) > 1 else "os1-boot.wav"
    mono = full_sweep()
    stereo = np.stack([mono, mono], axis=1)          # gentle, centered
    pcm = np.int16(np.clip(stereo, -1.0, 1.0) * 32767)
    wavfile.write(out_path, SAMPLE_RATE, pcm)
    print(f"wrote {out_path}  ({pcm.shape[0]/SAMPLE_RATE:.2f}s, {SAMPLE_RATE} Hz)")


if __name__ == "__main__":
    main()
