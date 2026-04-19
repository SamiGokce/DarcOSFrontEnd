import { useCpu } from "../context/CpuContext";
import { useState } from "react";
import "../assets/base.css"; // ensures glass + global styles

export default function SimStep() {
  const { cpu, step, reset, loadProgram } = useCpu();
  const [src, setSrc] = useState(
    "01010203000000000000000000000000\n3F000000000000000000000000000000"
  );

  const load = () => {
    const lines = src.split(/\n/).map(x => x.trim()).filter(Boolean);
    const words = lines.map(l => BigInt("0x" + l));
    loadProgram(words);
  };

  return (
    <div style={{ padding: "3rem 2rem" }} className="fade-in">
      <h1 style={{ fontWeight: 600, letterSpacing: "-0.02em" }}>
        Instruction Stepping
      </h1>
      <p style={{ opacity: 0.7, marginBottom: "1.5rem" }}>
        Load or edit machine code instructions, then step through execution.
      </p>

      {/* Layout grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "2fr 1fr",
          gap: "2rem",
          alignItems: "start",
        }}
      >
        {/* Left side — instruction input */}
        <div className="glass" style={{ padding: "1.5rem", borderRadius: "16px" }}>
          <h2 style={{ marginTop: 0, fontWeight: 600 }}>Program Memory</h2>
          <textarea
            value={src}
            onChange={e => setSrc(e.target.value)}
            rows="8"
            style={{
              width: "100%",
              fontFamily: "monospace",
              fontSize: "0.95rem",
              padding: "0.8rem",
              borderRadius: "12px",
              border: "1px solid rgba(0,0,0,0.1)",
              background: "rgba(255,255,255,0.4)",
              resize: "none",
              outline: "none",
              color: "#1a1a1a",
              boxShadow: "inset 0 2px 8px rgba(0,0,0,0.05)",
            }}
          />
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: "0.8rem",
              marginTop: "1rem",
            }}
          >
            <button className="sim-button" onClick={load}>
              Load Program
            </button>
            <button className="sim-button" onClick={step}>
              Step
            </button>
            <button className="sim-button" onClick={reset}>
              Reset
            </button>
          </div>
        </div>

        {/* Right side — status panel */}
        <div
          className="glass"
          style={{
            padding: "1.5rem",
            borderRadius: "16px",
            minHeight: "200px",
          }}
        >
          <h2 style={{ marginTop: 0, fontWeight: 600 }}>CPU State</h2>
          <p style={{ marginBottom: "0.6rem" }}>
            <b>PC:</b> {cpu.pc.toString()}
          </p>
          <p style={{ marginBottom: "0.6rem" }}>
            <b>Last Instruction:</b> {cpu.history.at(-1)?.note || "—"}
          </p>
          <p style={{ opacity: 0.7 }}>
            The program counter and recent execution note update as you step.
          </p>
        </div>
      </div>
    </div>
  );
}
