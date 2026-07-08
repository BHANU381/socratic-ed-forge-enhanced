import { useState, useRef, useEffect, memo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { BookOpen, Edit3, Save, MessageSquare, X, CheckCircle, AlertTriangle, ArrowRight } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

export const PreviewPanel = memo(function PreviewPanel({ preview, isLive, telemetry }) {
  const containerRef = useRef(null)
  const [editMode, setEditMode] = useState(false)
  const [content, setContent] = useState(preview || '')
  const [filename, setFilename] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  
  // Highlight selection states
  const [selectionRange, setSelectionRange] = useState(null)
  const [selectionCoords, setSelectionCoords] = useState({ top: 0, left: 0 })
  const [selectedText, setSelectedText] = useState('')
  const [showHighlightModal, setShowHighlightModal] = useState(false)
  const [replacementText, setReplacementText] = useState('')

  // Sidebar chat states for recovery
  const [showChat, setShowChat] = useState(false)
  const [chatPrompt, setChatPrompt] = useState('')
  const [chatStatus, setChatStatus] = useState('')

  const sessionId = telemetry?.session_dir?.split(/[\\/]/).pop() || ''
  const isPaused = telemetry?.status === 'paused_for_repair'

  useEffect(() => {
    setContent(preview || '')
  }, [preview])

  // Resolve filename from session
  useEffect(() => {
    if (sessionId) {
      fetch(`/api/sessions/${sessionId}/preview`)
        .then((res) => res.json())
        .then((data) => {
          if (data.filename) setFilename(data.filename)
        })
        .catch((err) => console.error('Error fetching session filename:', err))
    }
  }, [sessionId])

  const handleSave = async () => {
    if (!sessionId || !filename) return
    setIsSaving(true)
    try {
      const res = await fetch('/api/sessions/edit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          submodule_filename: filename,
          content: content
        })
      })
      if (res.ok) {
        setEditMode(false)
      } else {
        alert('Failed to save content updates.')
      }
    } catch (err) {
      console.error(err)
    } finally {
      setIsSaving(false)
    }
  }

  // Text selection handler for floating patch popup
  const handleTextSelection = () => {
    const selection = window.getSelection()
    if (!selection || selection.isCollapsed) {
      setSelectionRange(null)
      return
    }
    const text = selection.toString().strip()
    if (text.length > 5) {
      const range = selection.getRangeAt(0)
      const rect = range.getBoundingClientRect()
      
      setSelectedText(text)
      setReplacementText(text)
      setSelectionRange(range)
      setSelectionCoords({
        top: window.scrollY + rect.top - 45,
        left: window.scrollX + rect.left + rect.width / 2
      })
    }
  }

  const applySelectionPatch = () => {
    if (!selectedText || !replacementText) return
    const newContent = content.replace(selectedText, replacementText)
    setContent(newContent)
    setShowHighlightModal(false)
    setSelectionRange(null)
    
    // Automatically save spliced content
    fetch('/api/sessions/edit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        submodule_filename: filename || `${telemetry.course_name || 'textbook'}.md`,
        content: newContent
      })
    }).catch(console.error)
  }

  // Active validation recovery controls
  const handleResolveBreakpoint = async (resolution) => {
    if (!sessionId) return
    setChatStatus('Sending resolution…')
    
    // In active recovery loop, we modify breakpoint.json
    try {
      // First save active content changes if user edited the file
      if (editMode) {
        await fetch('/api/sessions/edit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: sessionId,
            submodule_filename: filename || 'breakpoint.json',
            content: content
          })
        })
      }

      // Write resolution to breakpoint
      const res = await fetch('/api/sessions/edit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          submodule_filename: 'breakpoint.json',
          content: JSON.stringify({
            status: 'resolved',
            resolution: resolution,
            user_instructions: chatPrompt
          })
        })
      })

      if (res.ok) {
        setChatPrompt('')
        setChatStatus('Resolution sent successfully! Resuming pipeline.')
        setTimeout(() => setChatStatus(''), 4000)
      } else {
        setChatStatus('Failed to send resolution request.')
      }
    } catch (err) {
      setChatStatus(`Error: ${err.message}`)
    }
  }

  if (!preview) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-zinc-500 italic gap-4 h-full bg-zinc-950">
        <div className="flex gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-zinc-600 animate-pulse" style={{ animationDelay: '0s' }} />
          <span className="w-1.5 h-1.5 rounded-full bg-zinc-600 animate-pulse" style={{ animationDelay: '0.2s' }} />
          <span className="w-1.5 h-1.5 rounded-full bg-zinc-600 animate-pulse" style={{ animationDelay: '0.4s' }} />
        </div>
        Waiting for production to start…
      </div>
    )
  }

  return (
    <div className="flex flex-row h-full w-full bg-zinc-950 text-zinc-50 min-w-0 min-h-0 relative">
      {/* Main Preview Pane */}
      <div className="flex-1 flex flex-col h-full min-w-0 min-h-0 relative">
        <div className="flex items-center gap-3 px-8 py-4 border-b border-zinc-800/50 bg-zinc-950 shrink-0 sticky top-0 z-10 shadow-sm">
          <BookOpen className="w-4 h-4 text-zinc-400" />
          <h2 className="text-sm font-semibold text-zinc-200 tracking-wide">
            {editMode ? 'Edit Textbook Markdown' : 'Live Book Preview'}
          </h2>
          {isLive && (
            <Badge variant="outline" className="ml-2 bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[10px] tracking-widest px-2.5 py-0 h-5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse mr-1.5 inline-block" />
              LIVE DRAFT
            </Badge>
          )}

          {isPaused && (
            <Badge variant="outline" className="ml-2 bg-amber-500/10 text-amber-400 border-amber-500/20 text-[10px] tracking-widest px-2.5 py-0 h-5 rounded-full flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              PAUSED FOR REPAIR
            </Badge>
          )}

          <div className="flex-1" />

          {/* Action buttons */}
          <div className="flex gap-2">
            {editMode ? (
              <>
                <button
                  onClick={handleSave}
                  disabled={isSaving}
                  className="text-xs bg-emerald-500 hover:bg-emerald-600 text-zinc-950 font-bold px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 shadow-sm"
                >
                  <Save className="w-3.5 h-3.5" />
                  {isSaving ? 'Saving…' : 'Save'}
                </button>
                <button
                  onClick={() => { setEditMode(false); setContent(preview) }}
                  className="text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-3 py-1.5 rounded-lg border border-zinc-700/50 transition-colors"
                >
                  Cancel
                </button>
              </>
            ) : (
              <button
                onClick={() => setEditMode(true)}
                className="text-xs bg-zinc-900 hover:bg-zinc-800 text-zinc-300 px-3 py-1.5 rounded-lg border border-zinc-800/80 transition-colors flex items-center gap-1.5"
              >
                <Edit3 className="w-3.5 h-3.5" />
                Edit
              </button>
            )}

            {isPaused && (
              <button
                onClick={() => setShowChat(!showChat)}
                className={`text-xs px-3 py-1.5 rounded-lg border transition-colors flex items-center gap-1.5 ${showChat ? 'bg-amber-500/20 text-amber-300 border-amber-500/30' : 'bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border-zinc-800/80'}`}
              >
                <MessageSquare className="w-3.5 h-3.5" />
                Repair Chat
              </button>
            )}
          </div>
        </div>

        {/* Text Area or Markdown view */}
        <div className="flex-1 overflow-auto py-12 px-4 md:px-8 lg:px-12 scroll-smooth min-h-0 min-w-0 custom-scrollbar flex flex-col items-center" ref={containerRef} onMouseUp={editMode ? null : handleTextSelection}>
          <div className="w-full max-w-3xl flex-1 flex flex-col">
            {editMode ? (
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                className="flex-1 w-full min-h-[500px] p-6 text-sm font-mono bg-zinc-900/50 border border-zinc-850 rounded-2xl text-zinc-200 focus:outline-none focus:border-zinc-700 focus:ring-1 focus:ring-zinc-700 transition-all custom-scrollbar whitespace-pre-wrap leading-relaxed resize-none"
              />
            ) : (
              <div className="w-full prose prose-invert prose-zinc prose-p:text-justify prose-li:text-justify select-text">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {content}
                </ReactMarkdown>
              </div>
            )}
          </div>
        </div>

        {/* Floating Highlight Patcher Popup */}
        {selectionRange && (
          <div
            style={{
              position: 'absolute',
              top: `${selectionCoords.top}px`,
              left: `${selectionCoords.left}px`,
              transform: 'translateX(-50%)',
              zIndex: 50
            }}
            className="bg-zinc-900 border border-zinc-800 rounded-xl p-1.5 flex gap-1 shadow-2xl animate-in fade-in zoom-in-95 duration-100"
          >
            <button
              onClick={() => setShowHighlightModal(true)}
              className="text-[10px] font-bold bg-emerald-500 hover:bg-emerald-600 text-zinc-950 px-2.5 py-1.5 rounded-lg flex items-center gap-1 transition-colors"
            >
              <Edit3 className="w-3 h-3" />
              Edit Selection
            </button>
            <button
              onClick={() => setSelectionRange(null)}
              className="p-1.5 text-zinc-400 hover:text-zinc-200 rounded-lg hover:bg-zinc-800 transition-colors"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        )}

        {/* Selection Edit Modal */}
        {showHighlightModal && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-2xl w-full p-6 flex flex-col gap-4 shadow-2xl animate-in zoom-in-95 duration-150">
              <div className="flex justify-between items-center">
                <h3 className="font-semibold text-zinc-200 text-sm">Edit Highlighted Selection</h3>
                <button onClick={() => setShowHighlightModal(false)} className="text-zinc-500 hover:text-zinc-300"><X className="w-4 h-4" /></button>
              </div>
              <textarea
                value={replacementText}
                onChange={(e) => setReplacementText(e.target.value)}
                className="w-full h-44 p-4 text-xs font-mono bg-zinc-950 border border-zinc-800 rounded-xl text-zinc-300 focus:outline-none focus:border-zinc-700 resize-none custom-scrollbar"
              />
              <div className="flex justify-end gap-2 text-xs">
                <button
                  onClick={applySelectionPatch}
                  className="bg-emerald-500 hover:bg-emerald-600 text-zinc-950 font-bold px-4 py-2 rounded-xl transition-colors"
                >
                  Apply & Save
                </button>
                <button
                  onClick={() => setShowHighlightModal(false)}
                  className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-4 py-2 rounded-xl transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Collapsible Sidebar Chat Panel for Breakpoint/Validation Recovery */}
      {showChat && isPaused && (
        <div className="w-80 shrink-0 border-l border-zinc-850 bg-zinc-900/40 backdrop-blur-xl flex flex-col h-full z-20">
          <div className="flex-shrink-0 flex items-center justify-between px-6 py-4 border-b border-zinc-850 bg-zinc-900/80">
            <span className="text-xs font-bold text-zinc-300 tracking-wide uppercase flex items-center gap-1.5">
              <MessageSquare className="w-4 h-4 text-amber-400" />
              Repair Assistant
            </span>
            <button onClick={() => setShowChat(false)} className="text-zinc-500 hover:text-zinc-300">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 overflow-auto p-6 flex flex-col gap-4 custom-scrollbar">
            {/* Blocker details */}
            <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4 flex flex-col gap-2">
              <div className="flex items-center gap-1.5 text-[10px] font-bold text-amber-400 uppercase tracking-widest">
                <AlertTriangle className="w-3.5 h-3.5" />
                Active Blockers
              </div>
              <ul className="text-xs text-zinc-300 space-y-1.5 list-disc list-inside">
                {telemetry?.failure_reasons?.filter(r => r.severity === 'blocker').map((b, idx) => (
                  <li key={idx} className="leading-relaxed">{b.message}</li>
                )) || <li className="italic text-zinc-500">No specific blockers logged.</li>}
              </ul>
            </div>

            {chatStatus && (
              <div className="text-[10px] font-mono text-zinc-400 bg-zinc-950 p-3 rounded-lg border border-zinc-850">
                {chatStatus}
              </div>
            )}

            <div className="flex-1" />

            {/* Prompt input and resolution buttons */}
            <div className="flex flex-col gap-2.5">
              <textarea
                value={chatPrompt}
                onChange={(e) => setChatPrompt(e.target.value)}
                placeholder="Type instructions to guide the Patch Editor (e.g. 'Use AWS instead of Google services')..."
                className="w-full h-24 p-3 text-xs bg-zinc-950 border border-zinc-850 rounded-xl text-zinc-300 placeholder-zinc-600 focus:outline-none focus:border-zinc-700 resize-none"
              />
              <div className="flex flex-col gap-2">
                <button
                  onClick={() => handleResolveBreakpoint('retry')}
                  className="w-full text-xs bg-emerald-500 hover:bg-emerald-600 text-zinc-950 font-bold py-2 rounded-xl transition-colors flex items-center justify-center gap-1 shadow-sm"
                >
                  Retry Validation
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => handleResolveBreakpoint('force_approve')}
                  className="w-full text-xs bg-zinc-800 hover:bg-zinc-750 text-zinc-200 border border-zinc-700/50 py-2 rounded-xl transition-colors flex items-center justify-center gap-1.5"
                >
                  <CheckCircle className="w-3.5 h-3.5 text-zinc-400" />
                  Force Approve Section
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
})
