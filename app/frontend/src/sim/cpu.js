import Memory from "./memory.js";
import { decode, execute } from "./isa.js";

export default class CPU {
  constructor(regCount = 8, memBytes = 1024 * 64) {
    this.regs = Array(regCount).fill(0n);
    this.mem = new Memory(memBytes);
    this.pc = 0n;
    this.halted = false;
    this.program = [];
    this.history = [];
  }

  getReg(i) { return this.regs[i] ?? 0n; }
  setReg(i, v) { if (i !== 0) this.regs[i] = v; } // r0 = constant zero

  loadProgram(words) {
    this.program = words;
    this.pc = 0n;
    this.halted = false;
    this.history = [];
  }

  fetch() {
    const idx = Number(this.pc / 16n);
    return this.program[idx] ?? 0n;
  }

  step() {
    if (this.halted) return { note: "HALT" };
    const raw = this.fetch();
    const instr = decode(raw);
    const result = execute(this, instr);
    this.pc = result.nextPc;
    this.history.push(result);
    return result;
  }

  reset() {
    this.regs.fill(0n);
    this.pc = 0n;
    this.halted = false;
    this.history = [];
  }
}
