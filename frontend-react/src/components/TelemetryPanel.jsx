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
    <div className="relative flex flex-col p-8 gap-6 shrink-0">
      <div className="flex items-center justify-between">
        <h3 className="text-[10px] font-semibold tracking-widest text-zinc-500 uppercase flex items-center gap-2">
          <Activity className="w-3.5 h-3.5" />
          Operational Insights
        </h3>
        <Badge variant="outline" className={`border-zinc-800 bg-zinc-900 text-[10px] px-2.5 py-0.5 rounded-full tracking-wider ${isRunning ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' : 'text-zinc-400'}`}>
          {isRunning ? (
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Running
            </span>
          ) : status}
        </Badge>
      </div>
      
      {/* 1px grid trick for Cockpit mode */}
      <div className="grid grid-cols-2 gap-px bg-zinc-800/50 rounded-2xl overflow-hidden border border-zinc-800/50 shadow-[0_4px_20px_-10px_rgba(0,0,0,0.5)]">
        <div className="bg-zinc-950 p-4 flex flex-col gap-1.5">
          <span className="text-[9px] font-semibold text-zinc-500 uppercase tracking-widest">Active Agent</span>
          <span className={`text-sm font-medium font-mono tracking-tight ${isRunning ? 'text-zinc-200' : 'text-zinc-400'}`}>{t.current_agent || '—'}</span>
        </div>
        <div className="bg-zinc-950 p-4 flex flex-col gap-1.5">
          <span className="text-[9px] font-semibold text-zinc-500 uppercase tracking-widest">Model</span>
          <span className="text-xs font-medium font-mono text-zinc-400 truncate" title={t.model_name}>{t.model_name || '—'}</span>
        </div>
        <div className="bg-zinc-950 p-4 flex flex-col gap-1.5">
          <span className="text-[9px] font-semibold text-zinc-500 uppercase tracking-widest">Completion</span>
          <span className={`text-sm font-medium font-mono ${isRunning || status === 'Completed' ? 'text-emerald-400' : 'text-zinc-300'}`}>{pct}%</span>
        </div>
        <div className="bg-zinc-950 p-4 flex flex-col gap-1.5">
          <span className="text-[9px] font-semibold text-zinc-500 uppercase tracking-widest">Total Tokens</span>
          <span className="text-sm font-medium font-mono text-zinc-200">{fmtNum(t.total_tokens)}</span>
        </div>
        <div className="bg-zinc-950 p-4 flex flex-col gap-1.5">
          <span className="text-[9px] font-semibold text-zinc-500 uppercase tracking-widest">Input</span>
          <span className="text-xs font-medium font-mono text-zinc-400">{fmtNum(t.input_tokens)}</span>
        </div>
        <div className="bg-zinc-950 p-4 flex flex-col gap-1.5">
          <span className="text-[9px] font-semibold text-zinc-500 uppercase tracking-widest">Output</span>
          <span className="text-xs font-medium font-mono text-zinc-400">{fmtNum(t.output_tokens)}</span>
        </div>
      </div>

      {/* Loop Stats Grid */}
      <div className="grid grid-cols-4 gap-px bg-zinc-800/50 rounded-xl overflow-hidden border border-zinc-800/50 shadow-[0_2px_10px_-5px_rgba(0,0,0,0.5)]">
        <div className="bg-zinc-950 p-2 flex flex-col items-center gap-1">
          <span className="text-[9px] font-semibold text-zinc-500 uppercase tracking-widest text-center">Pass (1st)</span>
          <span className="text-sm font-medium font-mono text-emerald-400">{fmtNum(t.passed_1st_iteration)}</span>
        </div>
        <div className="bg-zinc-950 p-2 flex flex-col items-center gap-1">
          <span className="text-[9px] font-semibold text-zinc-500 uppercase tracking-widest text-center">Pass (2nd)</span>
          <span className="text-sm font-medium font-mono text-emerald-500">{fmtNum(t.passed_2nd_iteration)}</span>
        </div>
        <div className="bg-zinc-950 p-2 flex flex-col items-center gap-1">
          <span className="text-[9px] font-semibold text-zinc-500 uppercase tracking-widest text-center">Pass (3rd)</span>
          <span className="text-sm font-medium font-mono text-amber-400">{fmtNum(t.passed_3rd_iteration)}</span>
        </div>
        <div className="bg-zinc-950 p-2 flex flex-col items-center gap-1">
          <span className="text-[9px] font-semibold text-zinc-500 uppercase tracking-widest text-center">Failed</span>
          <span className="text-sm font-medium font-mono text-rose-400">{fmtNum(t.failed_max_iterations)}</span>
        </div>
      </div>

      <div className="space-y-3">
        <Progress value={pct} className="h-1 bg-zinc-900 border border-zinc-800/50 rounded-full" indicatorClassName="bg-zinc-300 rounded-full" />
      </div>

      {(t.current_module || t.current_submodule) && (
        <div className="text-[11px] text-zinc-400 space-y-1.5 tracking-wide">
          {t.current_module && <div className="truncate"><span className="text-zinc-600 mr-2">Mod:</span> {t.current_module}</div>}
          {t.current_submodule && (
            <div className="flex items-center justify-between">
              <div className="truncate"><span className="text-zinc-600 mr-2">Sub:</span> <span className="text-zinc-300 font-medium">{t.current_submodule}</span></div>
              {t.active_iterations > 0 && (
                <Badge variant="outline" className="text-[9px] bg-zinc-900 border-zinc-700 text-zinc-400">
                  Attempt {t.active_iterations}
                </Badge>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
