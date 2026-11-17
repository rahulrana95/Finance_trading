const inr = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 })
const inr2 = new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

/** Whole rupees, Indian grouping: 2000000 -> "₹20,00,000". */
export const rupees = (value: number): string => `₹${inr.format(Math.round(value))}`
/** A price with paise: 1607.9 -> "₹1,607.90". */
export const price = (value: number): string => `₹${inr2.format(value)}`
/** Profit or loss with a sign and arrow, so the direction never depends on colour alone. */
export const signedRupees = (value: number): string =>
  value === 0 ? '₹0' : `${value > 0 ? '▲ +' : '▼ −'}₹${inr.format(Math.abs(Math.round(value)))}`
export const pct = (value: number, digits = 1): string => `${value.toFixed(digits)}%`
export const tone = (value: number): 'gain' | 'loss' | 'flat' => (value > 0 ? 'gain' : value < 0 ? 'loss' : 'flat')
export const dateTime = (iso: string): string =>
  new Date(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Kolkata' })
export const day = (iso: string): string =>
  new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'Asia/Kolkata' })
