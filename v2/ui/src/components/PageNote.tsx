/** Two or three plain lines under a page title: what the page does and how fresh its data is. */
export function PageNote({ lines }: { lines: readonly string[] }) {
  return (
    <ul className="page-note" aria-label="About this page">
      {lines.map((line) => (
        <li key={line}>{line}</li>
      ))}
    </ul>
  )
}
