import { useState } from "react";
import { useCpu } from "../context/CpuContext";

export default function SimStep() {
  const { cpu, step, reset, loadProgram } = useCpu();
  const [src, setSrc] = useState(
    "01010203000000000000000000000000\n3F000000000000000000000000000000"
  );

  const load = () => {
    const lines = src.split(/\n/).map((x) => x.trim()).filter(Boolean);
    const words = lines.map((l) => BigInt("0x" + l));
    loadProgram(words);
  };

  return (
    <div className="page fade-in">
      <h1 className="page__title">Instruction Stepping</h1>
      <p className="page__lead">
        Load or edit machine code instructions, then step through execution.
      </p>

      <div className="page-grid page-grid--2">
        <div className="glass glass-panel">
          <h2 className="glass-panel__title">Program Memory</h2>
          <textarea
            className="field"
            value={src}
            onChange={(e) => setSrc(e.target.value)}
            rows={8}
          />
          <div className="stack stack--row stack--end">
            <button type="button" className="sim-button" onClick={load}>
              Load Program
            </button>
            <button type="button" className="sim-button" onClick={step}>
              Step
            </button>
            <button type="button" className="sim-button" onClick={reset}>
              Reset
            </button>
          </div>
        </div>

        <div className="glass glass-panel">
          <h2 className="glass-panel__title">CPU State</h2>
          <p className="stat-row">
            <b>PC:</b> {cpu.pc.toString()}
          </p>
          <p className="stat-row">
            <b>Last Instruction:</b> {cpu.history.at(-1)?.note || "—"}
          </p>
          <p className="stat-row__hint">
            The program counter and recent execution note update as you step.
          </p>
        </div>
      </div>
    </div>
  );
}
