/** Small text renderer: preserves paragraphs/lists without interpreting source HTML. */
export function AssistantMessageText({ text }: { text: string }) {
  return <div className="space-y-3 text-left leading-7 [overflow-wrap:anywhere]">
    {text.split(/\n\s*\n/).filter(part => part.trim()).map((part, index) => {
      const rows = part.trim().split('\n')
      if (rows.every(row => /^\s*(?:[•*-]|\d+[.)])\s+/.test(row))) {
        return <ul key={index} className="list-disc space-y-2 pl-5">
          {rows.map((row, rowIndex) => <li key={rowIndex}>{row.replace(/^\s*(?:[•*-]|\d+[.)])\s+/, '')}</li>)}
        </ul>
      }
      const heading = rows.length > 1 && /:$/.test(rows[0]) && rows[0].length < 100
      return <div key={index}>
        {heading && <p className="mb-1 font-semibold text-slate-800 dark:text-slate-100">{rows[0]}</p>}
        <p className="whitespace-pre-line">{(heading ? rows.slice(1) : rows).join('\n')}</p>
      </div>
    })}
  </div>
}
