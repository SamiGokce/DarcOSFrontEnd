import { useCpu } from "../context/CpuContext";
import { useState } from "react";

export default function MemoryConsole() {
  const { cpu } = useCpu();
  const [memory] = useState(new Array(16).fill(0n)); // basic dummy memory

  return (
    <div style={{ padding: "2rem" }}>
      <h1>Memory & Console</h1>

      {/* Console Output */}
      <div
        style={{
          background: "rgba(0,0,0,0.85)",
          color: "#00ff88",
          padding: "1rem",
          borderRadius: "8px",
          minHeight: "120px",
          fontFamily: "monospace",
          marginBottom: "2rem",
        }}
      >
        <strong>Console Output:</strong>
        <div style={{ marginTop: "0.5rem" }}>
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

      {/* Memory Table */}
      <h2>Memory View</h2>
      <table
        style={{
          borderCollapse: "collapse",
          width: "100%",
          textAlign: "left",
        }}
      >
        <thead>
          <tr>
            <th style={{ borderBottom: "1px solid #888" }}>Address</th>
            <th style={{ borderBottom: "1px solid #888" }}>Value</th>
          </tr>
        </thead>
        <tbody>
          {memory.map((val, i) => (
            <tr key={i}>
              <td style={{ padding: "4px 8px" }}>{i}</td>
              <td style={{ padding: "4px 8px", fontFamily: "monospace" }}>
                {val.toString(16).padStart(4, "0")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
