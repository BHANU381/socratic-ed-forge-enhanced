import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Activity } from 'lucide-react'

export function TelemetryPanel({ telemetry, isRunning }) {
  const t = telemetry || {}
  const status = t.status || 'Idle'
  const pct = Math.min(100, Math.max(0, t.progress_percent || 0))

  const fmtNum = (n) =>
    n != null ? Number(n).toLocaleString() : '—'

  return (
    <Card className="bg-card border-border/50 shadow-lg relative overflow-hidden">
      {/* Background glow when running */}
      {isRunning && (
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-400 to-indigo-500 animate-pulse" />
      )}
      
      <CardHeader className="pb-2 pt-4 px-4 flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-[0.7rem] font-bold tracking-widest text-muted-foreground uppercase flex items-center gap-2">
          <Activity className="w-3.5 h-3.5" />
          Operational Insights
        </CardTitle>
        <Badge variant={isRunning ? "default" : "secondary"} className={isRunning ? "bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border-emerald-500/20" : ""}>
          {isRunning ? (
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Running
            </span>
          ) : status}
        </Badge>
      </CardHeader>
      
      <CardContent className="px-4 pb-4">
        <div className="grid grid-cols-2 gap-2 mb-3">
          <div className="bg-muted/30 border border-border/40 rounded-md p-2.5">
            <div className="text-[0.6rem] font-semibold text-muted-foreground uppercase tracking-widest mb-1">Active Agent</div>
            <div className={`text-sm font-semibold font-mono ${isRunning ? 'text-indigo-400' : 'text-foreground'}`}>{t.current_agent || '—'}</div>
          </div>
          <div className="bg-muted/30 border border-border/40 rounded-md p-2.5">
            <div className="text-[0.6rem] font-semibold text-muted-foreground uppercase tracking-widest mb-1">Model</div>
            <div className="text-xs font-semibold font-mono text-foreground truncate" title={t.model_name}>{t.model_name || '—'}</div>
          </div>
          <div className="bg-muted/30 border border-border/40 rounded-md p-2.5">
            <div className="text-[0.6rem] font-semibold text-muted-foreground uppercase tracking-widest mb-1">Completion</div>
            <div className={`text-sm font-semibold font-mono ${isRunning || status === 'Completed' ? 'text-emerald-400' : status?.startsWith('Failed') ? 'text-red-400' : status === 'Stopped' ? 'text-amber-400' : 'text-foreground'}`}>{pct}%</div>
          </div>
          <div className="bg-muted/30 border border-border/40 rounded-md p-2.5">
            <div className="text-[0.6rem] font-semibold text-muted-foreground uppercase tracking-widest mb-1">Total Tokens</div>
            <div className="text-sm font-semibold font-mono text-foreground">{fmtNum(t.total_tokens)}</div>
          </div>
          <div className="bg-muted/30 border border-border/40 rounded-md p-2.5">
            <div className="text-[0.6rem] font-semibold text-muted-foreground uppercase tracking-widest mb-1">Input Tokens</div>
            <div className="text-xs font-semibold font-mono text-muted-foreground">{fmtNum(t.input_tokens)}</div>
          </div>
          <div className="bg-muted/30 border border-border/40 rounded-md p-2.5">
            <div className="text-[0.6rem] font-semibold text-muted-foreground uppercase tracking-widest mb-1">Output Tokens</div>
            <div className="text-xs font-semibold font-mono text-muted-foreground">{fmtNum(t.output_tokens)}</div>
          </div>
        </div>

        <Progress value={pct} className="h-1.5 bg-muted/50" indicatorClassName="bg-gradient-to-r from-indigo-500 to-purple-500" />

        {(t.current_module || t.current_submodule) && (
          <div className="mt-3 text-xs text-muted-foreground leading-relaxed">
            {t.current_module && <div><span className="text-muted-foreground/70">Module: </span><span className="text-foreground/90">{t.current_module}</span></div>}
            {t.current_submodule && <div><span className="text-muted-foreground/70">Submodule: </span><span className="text-indigo-400 font-medium">{t.current_submodule}</span></div>}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
