import { useState } from "react";
import { useCpu } from "../context/CpuContext";

export default function MemoryConsole() {
  const { cpu } = useCpu();
  const [memory] = useState(new Array(16).fill(0n));

  return (
    <div className="page page--compact">
      <h1 className="page__title">Memory & Console</h1>

      <div className="console">
        <strong>Console Output:</strong>
        <div className="console__body">
          {cpu.history.length === 0
            ? "→ No output yet"
            : cpu.history.map((h, i) => (
                <div key={i}>
                  {h.note.includes("HALT")
                    ? "Program halted."
                    : `Executed ${h.note}`}
                </div>
              ))}
        </div>
      </div>

      <h2 className="glass-panel__title">Memory View</h2>
      <table className="data-table">
        <thead>
          <tr>
            <th>Address</th>
            <th>Value</th>
          </tr>
        </thead>
        <tbody>
          {memory.map((val, i) => (
            <tr key={i}>
              <td>{i}</td>
              <td className="mono">{val.toString(16).padStart(4, "0")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
