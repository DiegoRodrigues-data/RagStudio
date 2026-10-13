import { cn } from '@/lib/utils'

interface JsonViewProps {
  value: unknown
  className?: string
  /** Max height utility class, e.g. `max-h-64`. */
  maxHeight?: string
  /**
   * When set, objects/arrays deeper than this level start collapsed (`<details>`);
   * when omitted the JSON is printed in full.
   */
  expandDepth?: number
}

function isContainer(v: unknown): v is Record<string, unknown> | unknown[] {
  return typeof v === 'object' && v !== null
}

function Node({
  value,
  depth,
  expandDepth
}: {
  value: unknown
  depth: number
  expandDepth: number
}): React.JSX.Element {
  if (!isContainer(value)) {
    const text = JSON.stringify(value)
    return (
      <span className={cn(typeof value === 'string' ? 'text-foreground' : 'text-primary')}>
        {text}
      </span>
    )
  }
  const entries = Array.isArray(value)
    ? value.map((v, i) => [String(i), v] as const)
    : Object.entries(value)
  const open = Array.isArray(value) ? '[' : '{'
  const close = Array.isArray(value) ? ']' : '}'
  if (entries.length === 0) return <span>{open + close}</span>
  return (
    <details open={depth < expandDepth} className="inline-block align-top">
      <summary className="cursor-pointer select-none text-muted-foreground marker:text-muted-foreground">
        {open}
        <span className="ml-1 text-[10px]">{entries.length}</span>
        <span className="ml-1">…{close}</span>
      </summary>
      <div className="pl-4">
        {entries.map(([k, v]) => (
          <div key={k} className="whitespace-pre-wrap">
            {!Array.isArray(value) && (
              <span className="text-muted-foreground">{JSON.stringify(k)}: </span>
            )}
            <Node value={v} depth={depth + 1} expandDepth={expandDepth} />
          </div>
        ))}
      </div>
    </details>
  )
}

/** Pretty-printed JSON in a muted monospace block, optionally collapsible per level. */
export function JsonView({
  value,
  className,
  maxHeight = 'max-h-80',
  expandDepth
}: JsonViewProps): React.JSX.Element {
  const base = cn(
    'overflow-auto rounded-md border bg-muted/50 p-3 font-mono text-xs leading-relaxed break-words',
    maxHeight,
    className
  )
  if (expandDepth !== undefined && isContainer(value)) {
    return (
      <div className={base}>
        <Node value={value} depth={0} expandDepth={expandDepth} />
      </div>
    )
  }
  const text = typeof value === 'string' ? value : JSON.stringify(value, null, 2)
  return <pre className={cn(base, 'whitespace-pre-wrap')}>{text}</pre>
}
