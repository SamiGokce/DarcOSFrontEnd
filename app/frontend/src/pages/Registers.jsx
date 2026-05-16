import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { useCpu } from "../context/CpuContext";

export default function Registers() {
  const { registers, pc, history } = useCpu();
  const [changed, setChanged] = useState(new Set());
  const prevRegsRef = useRef(registers);

  useEffect(() => {
    const changedNow = new Set();
    registers.forEach((val, i) => {
      if (val !== prevRegsRef.current[i]) changedNow.add(i);
    });
    setChanged(changedNow);
    prevRegsRef.current = registers;
  }, [registers]);

  return (
    <div className="page">
      <h1 className="page__title">CPU Registers</h1>
      <p className="page__lead">
        Live view of current register values — changes flash green.
      </p>

      <div className="page-grid page-grid--registers">
        {registers.map((val, i) => (
          <motion.div
            key={i}
            className="glass register-card"
            initial={{ backgroundColor: "var(--register-default)" }}
            animate={{
              backgroundColor: changed.has(i)
                ? "var(--register-changed)"
                : "var(--register-default)",
            }}
            transition={{ duration: 0.6 }}
            whileHover={{ scale: 1.03 }}
          >
            <b className="register-card__label">R{i}</b>
            <p className="register-card__value">{val}</p>
          </motion.div>
        ))}
      </div>

      <h2 className="page__section-title">Program Counter</h2>
      <div className="glass glass-panel glass-panel--inline">
        <strong>PC:</strong> {pc}
      </div>

      <h2 className="page__section-title">Execution History</h2>
      <div className="glass glass-panel glass-panel--scroll">
        <AnimatePresence>
          {history.map((h, i) => (
            <motion.div
              key={i}
              className="history-item"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              • {h.note || h}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
