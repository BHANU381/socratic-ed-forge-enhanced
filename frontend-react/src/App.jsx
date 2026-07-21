import { useStream } from './hooks/useStream.js'
import { TelemetryPanel } from './components/TelemetryPanel.jsx'
import { LogsPanel }      from './components/LogsPanel.jsx'
import { ControlBar }     from './components/ControlBar.jsx'
import { AuditAlert }     from './components/AuditAlert.jsx'
import { PreviewPanel }   from './components/PreviewPanel.jsx'
import { PipelineMatrix } from './components/PipelineMatrix.jsx'
import { HistoryDashboard } from './components/HistoryDashboard.jsx'
import { TooltipProvider } from '@/components/ui/tooltip'
import { useState, useRef, useEffect, useCallback } from 'react'
import { PanelLeftClose, PanelLeftOpen, BookOpen, BarChart3, History } from 'lucide-react'

export default function App() {
  const { isRunning, pid, telemetry, logs, preview, isLive, connected } = useStream()
  const [sidebarWidth, setSidebarWidth] = useState(420)
  const [activeTab, setActiveTab] = useState('preview')
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const dragRef = useRef(false)

  const handleMouseDown = useCallback((e) => {
    dragRef.current = true
    setIsDragging(true)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }, [])

  const handleMouseMove = useCallback((e) => {
    if (!dragRef.current) return
    const newWidth = Math.max(250, Math.min(e.clientX, window.innerWidth * 0.6))
    setSidebarWidth(newWidth)
  }, [])

  const handleMouseUp = useCallback(() => {
    dragRef.current = false
    setIsDragging(false)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }, [])

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [handleMouseMove, handleMouseUp])

  return (
    <TooltipProvider>
      <div className="relative h-[100dvh] w-full overflow-hidden bg-zinc-950 text-zinc-50 flex flex-col font-sans">
        {/* Top bar */}
        <header className="flex-shrink-0 flex items-center gap-4 px-6 h-16 bg-zinc-950/80 backdrop-blur-xl border-b border-zinc-800/50 z-20">
          <button 
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1.5 rounded-md hover:bg-zinc-800 text-zinc-400 hover:text-zinc-100 transition-colors active:scale-95"
            title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          >
            {isCollapsed ? <PanelLeftOpen className="w-5 h-5" /> : <PanelLeftClose className="w-5 h-5" />}
          </button>
          
          <span className="font-semibold tracking-tight text-xl text-zinc-100 ml-1">
            Socratic <span className="text-zinc-500 font-light">Ed-Forge</span>
          </span>
          <span className="text-[10px] font-medium bg-zinc-900 text-zinc-400 border border-zinc-800 rounded-full px-3 py-1 tracking-widest ml-2 shadow-[0_1px_2px_rgba(0,0,0,0.1)] hidden sm:inline-block">
            AI COURSE ENGINE
          </span>
          <div className="flex-1" />
          <div className="flex items-center gap-2 text-xs font-medium text-zinc-400">
            <span className={`w-2 h-2 rounded-full ${!connected ? 'bg-zinc-700' : isRunning ? 'bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.4)]' : 'bg-rose-500'}`} />
            {!connected
              ? 'Connecting…'
              : isRunning
                ? `Running · PID ${pid}`
                : telemetry?.status || 'Idle'}
          </div>
        </header>

        {/* Custom Resizable Layout */}
        <div className="flex-1 w-full h-full overflow-hidden flex flex-row relative z-0">
          {/* Left panel */}
          <div 
            style={{ width: isCollapsed ? '0px' : `${sidebarWidth}px` }}
            className={`shrink-0 flex flex-col bg-zinc-950 border-r border-zinc-800/50 overflow-y-auto overflow-x-hidden z-10 custom-scrollbar relative ${!isDragging ? 'transition-[width] duration-300 ease-in-out' : ''}`}
          >
            <div className="flex flex-col min-w-[250px] min-h-full flex-1">
              <TelemetryPanel telemetry={telemetry} isRunning={isRunning} />
              <div className="h-px w-full bg-zinc-800/50 shrink-0" />
              <ControlBar isRunning={isRunning} />
              <LogsPanel logs={logs} />
              <AuditAlert telemetry={telemetry} />
            </div>
          </div>

          {/* Drag Handle */}
          {!isCollapsed && (
            <div 
              onMouseDown={handleMouseDown}
              onDoubleClick={() => setIsCollapsed(true)}
              className="w-1 hover:w-1.5 bg-zinc-800/50 hover:bg-emerald-500/80 transition-all duration-150 ease-in-out active:bg-emerald-400 z-20 cursor-col-resize flex flex-col items-center justify-center shrink-0"
              title="Drag to resize, double-click to collapse"
            >
              <div className="h-8 w-[2px] bg-zinc-600/80 rounded-full pointer-events-none" />
            </div>
          )}

          {/* Right panel */}
          <div className="flex-1 flex flex-col overflow-hidden bg-zinc-950 relative z-0 min-w-0">
            {/* Tabs Header */}
            <div className="flex-shrink-0 flex items-center justify-between border-b border-zinc-800/50 bg-zinc-950 px-6 h-12">
              <div className="flex gap-6">
                <button
                  onClick={() => setActiveTab('preview')}
                  className={`text-xs font-semibold tracking-wider transition-colors relative h-12 flex items-center gap-1.5 ${activeTab === 'preview' ? 'text-emerald-400 font-bold border-b-2 border-emerald-400' : 'text-zinc-400 hover:text-zinc-200'}`}
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  Textbook Preview
                </button>
                <button
                  onClick={() => setActiveTab('matrix')}
                  className={`text-xs font-semibold tracking-wider transition-colors relative h-12 flex items-center gap-1.5 ${activeTab === 'matrix' ? 'text-emerald-400 font-bold border-b-2 border-emerald-400' : 'text-zinc-400 hover:text-zinc-200'}`}
                >
                  <BarChart3 className="w-3.5 h-3.5" />
                  Pipeline Matrix
                </button>
                <button
                  onClick={() => setActiveTab('history')}
                  className={`text-xs font-semibold tracking-wider transition-colors relative h-12 flex items-center gap-1.5 ${activeTab === 'history' ? 'text-emerald-400 font-bold border-b-2 border-emerald-400' : 'text-zinc-400 hover:text-zinc-200'}`}
                >
                  <History className="w-3.5 h-3.5" />
                  Generation History
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-hidden relative">
              <div className={`w-full h-full ${activeTab !== 'preview' ? 'hidden' : ''}`}>
                <PreviewPanel preview={preview} isLive={isLive} telemetry={telemetry} isActive={activeTab === 'preview'} />
              </div>
              <div className={`w-full h-full overflow-auto p-8 custom-scrollbar ${activeTab !== 'matrix' ? 'hidden' : ''}`}>
                <PipelineMatrix telemetry={telemetry} isActive={activeTab === 'matrix'} />
              </div>
              <div className={`w-full h-full ${activeTab !== 'history' ? 'hidden' : ''}`}>
                <HistoryDashboard isActive={activeTab === 'history'} setActiveTab={setActiveTab} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </TooltipProvider>
  )
}
