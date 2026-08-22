export const fmt = (v, d = 3) => (v == null ? "n/a" : (+v).toFixed(d));
export const pct = (v) => (v == null ? "n/a" : (100 * v).toFixed(0) + "%");

// Sequential ramp (validated): index by t in [0,1]; darker = more.
export const SEQ = ["#cde2fb","#9ec5f4","#6da7ec","#3987e5","#256abf","#184f95","#0d366b"];
export const rampAt = (t) =>
  SEQ[Math.max(0, Math.min(SEQ.length - 1, Math.floor(t * SEQ.length)))];
