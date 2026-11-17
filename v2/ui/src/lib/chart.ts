/** Maps a value to a y coordinate in a chart `height` tall, leaving `pad` at top and bottom. */
export function scaleY(value: number, lo: number, hi: number, height: number, pad = 10): number {
  const span = hi - lo
  return span === 0 ? height / 2 : height - pad - ((value - lo) / span) * (height - 2 * pad)
}

/** SVG path for a line through `values`, spread across `width`. */
export function linePath(values: number[], lo: number, hi: number, width: number, height: number): string {
  const last = Math.max(values.length - 1, 1)
  return values.map((v, i) => `${i === 0 ? 'M' : 'L'}${((i / last) * width).toFixed(1)} ${scaleY(v, lo, hi, height).toFixed(1)}`).join(' ')
}
