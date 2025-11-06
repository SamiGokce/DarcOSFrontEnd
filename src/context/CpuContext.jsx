import { createContext, useContext, useState } from "react";

const CpuContext = createContext();

export function CpuProvider({ children }) {
  const [registers, setRegisters] = useState(Array(8).fill(0)); // 8 general-purpose registers
  const [pc, setPc] = useState(0); // Program Counter
  const [program, setProgram] = useState([]); // Machine words
  const [history, setHistory] = useState([]);

  // Load compiled machine words into memory
  const loadProgram = (words) => {
    setProgram(words);
    setPc(0);
    setRegisters(Array(8).fill(0));
    setHistory([{ note: "Program loaded." }]);
  };

  // Simulate executing one instruction
  const step = () => {
    if (pc >= program.length) {
      setHistory((h) => [...h, { note: "HALT: Program complete." }]);
      return;
    }

    const instr = program[pc];
    let newRegs = [...registers];
    let opName = "UNKNOWN";

    // Decode & execute a few sample opcodes
    switch (instr) {
      // ADD (R1 = R2 + R3)
      case 0x01010203000000000000000000000000:
        newRegs[1] = newRegs[2] + newRegs[3];
        opName = "ADD R1 = R2 + R3";
        break;

      // ADDI (R1 = R2 + 5)
      case 0x02010203000000000000000000000000:
        newRegs[1] = newRegs[2] + 5;
        opName = "ADDI R1 = R2 + 5";
        break;

      // NOP (do nothing)
      case 0x00000000000000000000000000000000:
        opName = "NOP (no operation)";
        break;

      // HALT (stop execution)
      case 0x3F000000000000000000000000000000:
        opName = "HALT (stop execution)";
        setHistory((h) => [...h, { note: "HALT instruction reached." }]);
        return;

      default:
        opName = `UNKNOWN instruction: ${instr.toString(16)}`;
        break;
    }

    // Apply register update
    setRegisters(newRegs);
    setPc(pc + 1);
    setHistory((h) => [...h, { note: opName }]);
  };

  // Reset CPU state
  const reset = () => {
    setRegisters(Array(8).fill(0));
    setPc(0);
    setProgram([]);
    setHistory([]);
  };

  return (
    <CpuContext.Provider
      value={{
        registers,
        pc,
        program,
        history,
        loadProgram,
        step,
        reset,
        cpu: { registers, pc, history },
      }}
    >
      {children}
    </CpuContext.Provider>
  );
}

export function useCpu() {
  return useContext(CpuContext);
}
