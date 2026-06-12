import { useEffect, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Terminal } from 'lucide-react'

function classifyLine(line) {
  const l = line.toLowerCase()
  if (l.includes('generator'))  return 'text-emerald-400'
  if (l.includes('critic'))     return 'text-amber-400'
  if (l.includes('editor'))     return 'text-blue-400'
  if (l.includes('librarian'))  return 'text-purple-400'
  if (l.includes('error') || l.includes('critical')) return 'text-red-400 font-semibold'
  return 'text-slate-400'
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
    <Card className="bg-card border-border/50 shadow-lg flex-1 flex flex-col min-h-0">
      <CardHeader className="pb-2 pt-3 px-4 flex-shrink-0">
        <CardTitle className="text-[0.7rem] font-bold tracking-widest text-muted-foreground uppercase flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5" />
          Agent Logs
        </CardTitle>
      </CardHeader>
      
      <CardContent className="px-4 pb-4 flex-1 min-h-0 relative">
        <div className="absolute inset-x-4 inset-y-0 bottom-4 rounded-md border border-white/10 bg-black/40 backdrop-blur-sm overflow-hidden">
          <ScrollArea className="h-full w-full" ref={termRef}>
            <div className="p-3 pr-6 font-mono text-[0.7rem] leading-relaxed tracking-tight">
              {logs.length === 0 ? (
                <div className="text-slate-500">
                  <span className="text-cyan-500 mr-2">&gt;</span>
                  System idle. Upload a JSON config and launch production.
                </div>
              ) : (
                logs.map((line, i) => (
                  <div key={i} className={`py-0.5 ${classifyLine(line)}`}>
                    <span className="text-cyan-500/70 mr-2 select-none">&gt;</span>
                    <span className="break-words">{line}</span>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </div>
      </CardContent>
    </Card>
  )
}
