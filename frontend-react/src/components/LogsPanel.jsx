import { useEffect, useRef } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Terminal } from 'lucide-react'

function classifyLine(line) {
  const l = line.toLowerCase()
  if (l.includes('generator'))  return 'text-emerald-400'
  if (l.includes('critic'))     return 'text-amber-400'
  if (l.includes('editor'))     return 'text-blue-400'
  if (l.includes('librarian'))  return 'text-purple-400'
  if (l.includes('error') || l.includes('critical')) return 'text-red-400 font-semibold'
  return 'text-zinc-400'
}

export function LogsPanel({ logs }) {
  const termRef = useRef(null)

  useEffect(() => {
    // We use a querySelector to find the scrollable viewport inside Radix ScrollArea
    const viewport = termRef.current?.querySelector('[data-radix-scroll-area-viewport]')
    if (!viewport) return
    
    const nearBottom = viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight < 120
    if (nearBottom) {
      viewport.scrollTop = viewport.scrollHeight
    }
  }, [logs])

  return (
    <div className="flex-1 flex flex-col min-h-[300px] bg-zinc-950 shrink-0">
      <div className="flex-shrink-0 px-8 pt-6 pb-4">
        <h3 className="text-[10px] font-semibold tracking-widest text-zinc-500 uppercase flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5" />
          Agent Logs
        </h3>
      </div>
      
      <div className="flex-1 min-h-0 flex flex-col px-8 pb-8">
        <div className="flex-1 min-h-0 rounded border border-zinc-800 bg-zinc-900/30 overflow-hidden shadow-[inset_0_1px_0_rgba(255,255,255,0.02)] flex flex-col">
          <ScrollArea className="flex-1 h-full w-full" ref={termRef}>
            <div className="p-4 pr-6 font-mono text-[11px] leading-relaxed tracking-tight">
              {logs.length === 0 ? (
                <div className="text-zinc-600">
                  <span className="text-zinc-700 mr-2">&gt;</span>
                  System idle. Upload a JSON config and launch production.
                </div>
              ) : (
                logs.map((line, i) => (
                  <div key={i} className={`py-0.5 ${classifyLine(line)}`}>
                    <span className="text-zinc-700 mr-2 select-none">&gt;</span>
                    <span className="break-words">{line}</span>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </div>
      </div>
    </div>
  )
}
