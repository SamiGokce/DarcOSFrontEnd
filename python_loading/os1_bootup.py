"""
OS1 Bootup Sequence Synthesizer — inspired by the sound from "Her"

The slider represents system load percentage (0–100%).
  0%   → lowest pitch (beginning of the sweep)
  100% → highest pitch (end of the sweep)

Moving the slider plays a short tone at exactly the pitch that
corresponds to that loading state — as if you paused the boot sequence there.
"""

import numpy as np
import tkinter as tk
from tkinter import ttk
import threading

try:
    import sounddevice as sd
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "sounddevice"])
    import sounddevice as sd

try:
    import scipy.signal as signal
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "scipy"])
    import scipy.signal as signal


SAMPLE_RATE = 44100

# Full sweep frequency range — 0% maps to FREQ_START, 100% maps to FREQ_END
FREQ_START = 180.0
FREQ_END   = 1100.0

HARMONICS = [
    (1.00, 1.00),
    (0.45, 2.00),
    (0.20, 3.00),
    (0.08, 4.00),
    (0.04, 5.02),   # slight detuned 5th for shimmer
]


def freq_at_load(pct: float) -> float:
    """Return the instantaneous frequency (Hz) for a given load percentage 0–100."""
    t = np.clip(pct / 100.0, 0.0, 1.0)
    return FREQ_START + t * (FREQ_END - FREQ_START)


def tone_at_load(pct: float, duration: float = 0.55) -> np.ndarray:
    """Generate a short tone that sounds like OS1 is at `pct`% loaded.

    The fundamental frequency is exactly where the sweep would be at that
    load point.  A brief frequency glide around that centre makes it feel
    alive rather than a flat beep.
    """
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)

    centre = freq_at_load(pct)

    # Tiny glide: ±2.5% frequency wobble centred on the load-point freq
    glide_range = centre * 0.025
    freq_t = centre + np.linspace(-glide_range, glide_range, n)

    phase = 2 * np.pi * np.cumsum(freq_t) / SAMPLE_RATE

    wave = np.zeros(n)
    for amp, mult in HARMONICS:
        wave += amp * np.sin(phase * mult)

    wave /= np.max(np.abs(wave)) + 1e-9

    # Envelope: smooth attack + release
    attack  = int(0.12 * SAMPLE_RATE)
    release = int(0.22 * SAMPLE_RATE)
    env = np.ones(n)
    env[:attack]   = np.linspace(0, 1, attack)
    env[-release:] = np.linspace(1, 0, release)

    # Low-pass tracking the current frequency
    cutoff = min(centre * 2.2, 18000) / (SAMPLE_RATE / 2)
    b, a = signal.butter(4, cutoff, btype='low')
    wave = signal.lfilter(b, a, wave)

    wave *= env * 0.85
    return wave.astype(np.float32)


def full_sweep(duration: float = 2.8) -> np.ndarray:
    """Generate the complete 0→100% bootup sweep."""
    n = int(SAMPLE_RATE * duration)
    freq_t = np.linspace(FREQ_START, FREQ_END, n)
    phase  = 2 * np.pi * np.cumsum(freq_t) / SAMPLE_RATE

    wave = np.zeros(n)
    for amp, mult in HARMONICS:
        wave += amp * np.sin(phase * mult)

    wave /= np.max(np.abs(wave)) + 1e-9

    attack  = int(0.18 * SAMPLE_RATE)
    release = int(0.35 * SAMPLE_RATE)
    env = np.ones(n)
    env[:attack]   = np.linspace(0, 1, attack)
    env[-release:] = np.linspace(1, 0, release)

    # Dynamic low-pass that opens up as the sweep rises
    wave_out = np.empty_like(wave)
    chunk = 512
    for i in range(0, n, chunk):
        sl   = slice(i, min(i + chunk, n))
        fc   = float(np.mean(freq_t[sl]))
        cut  = min(fc * 2.2, 18000) / (SAMPLE_RATE / 2)
        b, a = signal.butter(2, cut, btype='low')
        wave_out[sl] = signal.lfilter(b, a, wave[sl])

    wave_out *= env * 0.85
    return wave_out.astype(np.float32)


# ── UI ────────────────────────────────────────────────────────────────────────

class OS1App:
    def __init__(self, root: tk.Tk):
        self.root  = root
        self._lock = threading.Lock()
        root.title("OS1 Bootup Synthesizer")
        root.resizable(False, False)

        BG     = "#0f0f1a"
        PANEL  = "#16213e"
        ACCENT = "#7b68ee"
        FG     = "#d8d8f0"
        DIM    = "#666688"

        root.configure(bg=BG)

        tk.Label(root, text="OS1", font=("Helvetica Neue", 28, "bold"),
                 fg=ACCENT, bg=BG).pack(pady=(22, 0))
        tk.Label(root, text="BOOTUP SEQUENCE  ·  from Her",
                 font=("Helvetica Neue", 9), fg=DIM, bg=BG).pack(pady=(2, 18))

        # ── load slider ──────────────────────────────────────────────────────
        frame = tk.Frame(root, bg=PANEL, bd=0)
        frame.pack(padx=30, pady=4, fill="x", ipady=14, ipadx=18)

        header = tk.Frame(frame, bg=PANEL)
        header.pack(fill="x", padx=4)
        tk.Label(header, text="System Load", font=("Helvetica Neue", 11),
                 fg=FG, bg=PANEL).pack(side="left")
        self._pct_label = tk.Label(header, text="0%",
                                   font=("Helvetica Neue", 11, "bold"),
                                   fg=ACCENT, bg=PANEL, width=6, anchor="e")
        self._pct_label.pack(side="right")

        self._freq_label = tk.Label(frame, text=f"≈ {FREQ_START:.0f} Hz",
                                    font=("Helvetica Neue", 9), fg=DIM, bg=PANEL)
        self._freq_label.pack(anchor="e", padx=4)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Load.Horizontal.TScale",
                        background=PANEL, troughcolor="#1e2a4a",
                        sliderlength=22, sliderrelief="flat")

        self._load_var = tk.DoubleVar(value=0.0)
        self._slider = ttk.Scale(frame, from_=0, to=100,
                                 variable=self._load_var, orient="horizontal",
                                 style="Load.Horizontal.TScale",
                                 command=self._on_load_change)
        self._slider.pack(fill="x", padx=4, pady=(4, 2))

        tick_frame = tk.Frame(frame, bg=PANEL)
        tick_frame.pack(fill="x", padx=4)
        for lbl in ("0%", "25%", "50%", "75%", "100%"):
            tk.Label(tick_frame, text=lbl, font=("Helvetica Neue", 8),
                     fg=DIM, bg=PANEL).pack(side="left", expand=True)

        # ── buttons ──────────────────────────────────────────────────────────
        btn_frame = tk.Frame(root, bg=BG)
        btn_frame.pack(pady=(16, 22))

        tk.Button(btn_frame, text="▶  PLAY TONE",
                  font=("Helvetica Neue", 11, "bold"),
                  fg="#fff", bg=ACCENT, activebackground="#9b88ff",
                  relief="flat", padx=18, pady=8,
                  command=self._play_tone).pack(side="left", padx=6)

        tk.Button(btn_frame, text="⟳  FULL SWEEP",
                  font=("Helvetica Neue", 11, "bold"),
                  fg="#fff", bg="#3a3a6a", activebackground="#5a5a9a",
                  relief="flat", padx=18, pady=8,
                  command=self._play_sweep).pack(side="left", padx=6)

        tk.Button(btn_frame, text="■  STOP",
                  font=("Helvetica Neue", 11, "bold"),
                  fg="#fff", bg="#333", activebackground="#555",
                  relief="flat", padx=18, pady=8,
                  command=self._stop).pack(side="left", padx=6)

    # ── callbacks ─────────────────────────────────────────────────────────────

    def _on_load_change(self, val):
        pct = round(float(val))
        self._load_var.set(pct)
        self._pct_label.config(text=f"{pct}%")
        self._freq_label.config(text=f"≈ {freq_at_load(pct):.0f} Hz")

    def _play_tone(self):
        pct = self._load_var.get()
        self._play_async(lambda: tone_at_load(pct))

    def _play_sweep(self):
        self._play_async(full_sweep)

    def _play_async(self, gen_fn):
        self._stop()
        def _run():
            wave = gen_fn()
            with self._lock:
                sd.play(wave, samplerate=SAMPLE_RATE)
            sd.wait()
        threading.Thread(target=_run, daemon=True).start()

    def _stop(self):
        sd.stop()


if __name__ == "__main__":
    root = tk.Tk()
    OS1App(root)
    root.mainloop()
