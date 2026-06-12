import { useStream } from './hooks/useStream.js'
import { TelemetryPanel } from './components/TelemetryPanel.jsx'
import { LogsPanel }      from './components/LogsPanel.jsx'
import { ControlBar }     from './components/ControlBar.jsx'
import { AuditAlert }     from './components/AuditAlert.jsx'
import { PreviewPanel }   from './components/PreviewPanel.jsx'
import { TooltipProvider } from '@/components/ui/tooltip'
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable'

export default function App() {
  const { isRunning, pid, telemetry, logs, preview, isLive, connected } = useStream()

  return (
    <TooltipProvider>
      {/* Dynamic Glassmorphism Background */}
      <div className="relative h-screen w-full overflow-hidden bg-background text-foreground flex flex-col">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-indigo-900/40 via-background to-background -z-10" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,_var(--tw-gradient-stops))] from-cyan-900/20 via-transparent to-transparent -z-10" />
        
        {/* Top bar */}
        <header className="flex-shrink-0 flex items-center gap-3 px-6 h-14 bg-background/40 backdrop-blur-md border-b border-white/5 shadow-sm z-20">
          <span className="font-bold tracking-tight text-lg">
            Socratic <span className="text-cyan-400 drop-shadow-[0_0_8px_rgba(6,182,212,0.5)]">Ed-Forge</span>
          </span>
          <span className="text-[0.65rem] font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 rounded-full px-2.5 py-0.5 tracking-widest">
            AI COURSE ENGINE
          </span>
          <div className="flex-1" />
          <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
            <span className={`w-2 h-2 rounded-full shadow-[0_0_5px_currentColor] ${!connected ? 'bg-muted text-muted' : isRunning ? 'bg-emerald-500 text-emerald-500 animate-pulse' : 'bg-red-500 text-red-500'}`} />
            {!connected
              ? 'Connecting…'
              : isRunning
                ? `Running · PID ${pid}`
                : telemetry?.status || 'Idle'}
          </div>
        </header>

        {/* Standard Flex Layout (Bulletproof) */}
        <div className="flex-1 w-full h-full overflow-hidden flex flex-row">
          {/* Left panel */}
          <div className="w-[380px] shrink-0 flex flex-col gap-4 bg-background/20 backdrop-blur-sm border-r border-white/5 overflow-y-auto overflow-x-hidden p-5 z-10">
            <TelemetryPanel telemetry={telemetry} isRunning={isRunning} />
            <ControlBar isRunning={isRunning} />
            <AuditAlert telemetry={telemetry} />
            <LogsPanel logs={logs} />
          </div>

          {/* Right panel */}
          <div className="flex-1 flex flex-col overflow-hidden bg-transparent relative z-0 min-w-0">
            <PreviewPanel preview={preview} isLive={isLive} />
          </div>
        </div>
      </div>
    </TooltipProvider>
  )
}
