import { useState, useEffect } from 'react'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Search, Calendar, Award, FileText, ChevronRight } from 'lucide-react'

export function HistoryDashboard() {
  const [sessions, setSessions] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [selectedPreview, setSelectedPreview] = useState(null)
  const [previewContent, setPreviewContent] = useState('')

  useEffect(() => {
    fetch('/api/sessions')
      .then((res) => res.json())
      .then((data) => {
        setSessions(data.sessions || [])
        setLoading(false)
      })
      .catch((err) => {
        console.error('Failed to load history:', err)
        setLoading(false)
      })
  }, [])

  const handleLoadPreview = (sessionId) => {
    setSelectedPreview(sessionId)
    setPreviewContent('Loading preview...')
    fetch(`/api/sessions/${sessionId}/preview`)
      .then((res) => res.json())
      .then((data) => {
        setPreviewContent(data.content || '*No content available or generation incomplete.*')
      })
      .catch((err) => {
        setPreviewContent(`Failed to load textbook preview: ${err.message}`)
      })
  }

  const filteredSessions = sessions.filter((s) => {
    const name = (s.metadata?.course_name || s.session_id).toLowerCase()
    const theme = (s.metadata?.prompt_theme || '').toLowerCase()
    const query = searchQuery.toLowerCase()
    return name.includes(query) || theme.includes(query)
  })

  if (selectedPreview) {
    return (
      <div className="w-full h-full flex flex-col bg-zinc-950">
        <div className="flex-shrink-0 flex items-center justify-between border-b border-zinc-800 px-8 h-14 bg-zinc-900/50">
          <div className="flex items-center gap-3">
            <span className="text-zinc-500 text-xs font-mono">{selectedPreview}</span>
            <ChevronRight className="w-4 h-4 text-zinc-600" />
            <span className="text-zinc-200 text-sm font-semibold">Textbook Preview</span>
          </div>
          <button
            onClick={() => setSelectedPreview(null)}
            className="text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-3 py-1.5 rounded-lg border border-zinc-700/50 transition-colors"
          >
            Back to History
          </button>
        </div>
        <div className="flex-1 overflow-auto p-8 custom-scrollbar">
          <div className="max-w-4xl mx-auto bg-zinc-900/40 border border-zinc-800/80 rounded-2xl p-8 shadow-xl">
            <pre className="text-zinc-300 text-sm font-mono whitespace-pre-wrap font-sans leading-relaxed selection:bg-emerald-500/20 selection:text-emerald-300">
              {previewContent}
            </pre>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full h-full overflow-auto p-8 custom-scrollbar flex flex-col gap-6">
      {/* Header and Search */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-zinc-100">Generation History</h2>
          <p className="text-xs text-zinc-500 mt-1">Browse, view, and load past generation sessions.</p>
        </div>
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
          <input
            type="text"
            placeholder="Search by course name or theme..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs bg-zinc-900 border border-zinc-800 rounded-xl text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-700 focus:ring-1 focus:ring-zinc-700 transition-all"
          />
        </div>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center text-zinc-500 text-xs font-mono">
          Loading historical runs...
        </div>
      ) : filteredSessions.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center border border-dashed border-zinc-800 rounded-3xl p-12 text-center">
          <FileText className="w-8 h-8 text-zinc-700 mb-3" />
          <p className="text-zinc-500 text-xs font-medium">No historical sessions found.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredSessions.map((s) => {
            const metadata = s.metadata || {}
            const pct = Math.min(100, Math.max(0, metadata.completion_rate || 0))
            const cleanName = metadata.course_name || s.session_id
            
            // Format timestamp from session ID
            let dateStr = 'Unknown Date'
            const parts = s.session_id.split('_')
            if (parts.length >= 3) {
              const ymd = parts[1]
              if (ymd.length === 8) {
                dateStr = `${ymd.slice(0, 4)}-${ymd.slice(4, 6)}-${ymd.slice(6, 8)}`
              }
            }

            return (
              <div
                key={s.session_id}
                className="flex flex-col bg-zinc-900/30 border border-zinc-800/80 rounded-2xl p-6 gap-4 hover:border-zinc-700/50 hover:bg-zinc-900/50 transition-all shadow-[0_4px_20px_-10px_rgba(0,0,0,0.5)]"
              >
                <div className="flex flex-col gap-1.5">
                  <div className="flex items-start justify-between gap-4">
                    <h3 className="font-semibold text-zinc-200 text-sm tracking-tight truncate flex-1" title={cleanName}>
                      {cleanName}
                    </h3>
                    <Badge variant="outline" className="border-zinc-800 bg-zinc-950 text-[10px] text-zinc-400 font-mono">
                      {metadata.prompt_theme || 'default'}
                    </Badge>
                  </div>
                  <span className="text-[10px] text-zinc-500 font-mono flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-zinc-600" />
                    {dateStr} ({s.session_id.split('_')[2] || ''})
                  </span>
                </div>

                <div className="flex flex-col gap-2">
                  <div className="flex justify-between text-[10px] font-semibold text-zinc-500 uppercase tracking-widest">
                    <span>Completion Rate</span>
                    <span className="text-zinc-300">{pct}%</span>
                  </div>
                  <Progress value={pct} className="h-1 bg-zinc-950 rounded-full" indicatorClassName="bg-emerald-400 rounded-full" />
                </div>

                <div className="flex gap-2 mt-2">
                  <button
                    onClick={() => handleLoadPreview(s.session_id)}
                    className="flex-1 text-[11px] font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-300 py-2 rounded-lg border border-zinc-700/40 transition-colors flex items-center justify-center gap-1.5"
                  >
                    <Award className="w-3.5 h-3.5" />
                    View Textbook
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
