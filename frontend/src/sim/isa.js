import { toU128 } from "./utils.js";

export const OPCODES = {
  NOP: 0x00,
  ADD: 0x01,
  ADDI: 0x02,
  HALT: 0x3F
};

export function decode(raw) {
  const opcode = Number((raw >> 120n) & 0xFFn);
  const rd = Number((raw >> 112n) & 0xFFn);
  const rs1 = Number((raw >> 104n) & 0xFFn);
  const rs2 = Number((raw >> 96n) & 0xFFn);
  const imm = raw & ((1n << 96n) - 1n);
  return { opcode, rd, rs1, rs2, imm };
}

export function execute(cpu, instr) {
  switch (instr.opcode) {
    case OPCODES.NOP:
      return { note: "NOP", nextPc: cpu.pc + 16n };

    case OPCODES.ADD: {
      const v = toU128(cpu.getReg(instr.rs1) + cpu.getReg(instr.rs2));
      cpu.setReg(instr.rd, v);
      return { note: `ADD r${instr.rd}`, nextPc: cpu.pc + 16n };
    }

    case OPCODES.ADDI: {
      const v = toU128(cpu.getReg(instr.rs1) + instr.imm);
      cpu.setReg(instr.rd, v);
      return { note: `ADDI r${instr.rd}`, nextPc: cpu.pc + 16n };
    }

    case OPCODES.HALT:
      cpu.halted = true;
      return { note: "HALT", nextPc: cpu.pc };

    default:
      return { note: "UNKNOWN", nextPc: cpu.pc + 16n };
  }
}
