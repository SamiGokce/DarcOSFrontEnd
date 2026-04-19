export default class Memory {
  constructor(sizeBytes = 1024 * 64) {  // 64 KB memory for now
    this.data = new Uint8Array(sizeBytes);
  }

  read8(addr) { return this.data[addr] ?? 0; }
  write8(addr, value) { this.data[addr] = value & 0xFF; }
}
