// Keep numbers inside 128-bit range
export const MASK128 = (x) => x & ((1n << 128n) - 1n);

// Convert anything to unsigned 128-bit
export const toU128 = (x) => MASK128(BigInt(x));

// Convert to signed 128-bit
export const toI128 = (x) => {
  const sign = 1n << 127n;
  const masked = MASK128(BigInt(x));
  return (masked & sign) ? (masked - (1n << 128n)) : masked;
};
