import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { useCpu } from "../context/CpuContext";
import "../assets/base.css"; // make sure your global CSS (with .glass etc.) is imported

export default function Registers() {
  const { registers, pc, history } = useCpu();
  const [changed, setChanged] = useState(new Set());
  const prevRegsRef = useRef(registers);

  // Detect register changes
  useEffect(() => {
    const changedNow = new Set();
    registers.forEach((val, i) => {
      if (val !== prevRegsRef.current[i]) changedNow.add(i);
    });
    setChanged(changedNow);
    prevRegsRef.current = registers;
  }, [registers]);

  return (
    <div className="fade-in" style={{ padding: "3rem 2rem" }}>
      <h1 style={{ fontWeight: 600, letterSpacing: "-0.02em" }}>CPU Registers</h1>
      <p style={{ opacity: 0.7 }}>
        Live view of current register values — changes flash green 💡
      </p>

      {/* Register Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
          gap: "1.2rem",
          marginTop: "2rem",
        }}
      >
        {registers.map((val, i) => (
          <motion.div
            key={i}
            className="glass"
            initial={{ backgroundColor: "rgba(255,255,255,0.35)" }}
            animate={{
              backgroundColor: changed.has(i)
                ? "rgba(144,238,144,0.5)" // subtle green pulse
                : "rgba(255,255,255,0.35)",
            }}
            transition={{ duration: 0.6 }}
            style={{
              padding: "1.2rem 1rem",
              textAlign: "center",
              borderRadius: "12px",
              boxShadow: "0 6px 20px rgba(0,0,0,0.05)",
              transition: "transform 0.2s ease",
            }}
            whileHover={{ scale: 1.03 }}
          >
            <b style={{ fontSize: "1rem", opacity: 0.8 }}>R{i}</b>
            <p style={{ fontWeight: 500, marginTop: "0.5rem", fontSize: "1.1rem" }}>
              {val}
            </p>
          </motion.div>
        ))}
      </div>

      {/* Program Counter */}
      <h2 style={{ marginTop: "3rem", fontWeight: 600 }}>Program Counter</h2>
      <div
        className="glass"
        style={{
          display: "inline-block",
          marginTop: "0.6rem",
          padding: "0.8rem 1.5rem",
          borderRadius: "10px",
        }}
      >
        <strong>PC:</strong> {pc}
      </div>

      {/* Execution History */}
      <h2 style={{ marginTop: "3rem", fontWeight: 600 }}>Execution History</h2>
      <div
        className="glass"
        style={{
          marginTop: "0.8rem",
          borderRadius: "12px",
          padding: "1rem 1.2rem",
          maxHeight: "200px",
          overflowY: "auto",
        }}
      >
        <AnimatePresence>
          {history.map((h, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              style={{ marginBottom: "0.3rem", opacity: 0.85 }}
            >
              • {h.note || h}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
