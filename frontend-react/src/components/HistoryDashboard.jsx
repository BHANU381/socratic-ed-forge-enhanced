import { useState, useEffect } from 'react'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Search, Calendar, FileText, ChevronRight, ChevronLeft, ChevronDown, Edit2, Check, X, Play, Loader2, BookOpen } from 'lucide-react'
import { parseSubmodules } from '@/lib/utils'

function formatSessionDate(sessionId) {
  const parts = sessionId.split('_')
  if (parts.length >= 3) {
    const ymd = parts[1]
    const hms = parts[2]
    if (ymd.length === 8 && hms.length === 6) {
      const year = ymd.slice(0, 4)
      const month = ymd.slice(4, 6)
      const day = ymd.slice(6, 8)
      const hourStr = hms.slice(0, 2)
      const minStr = hms.slice(2, 4)
      
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
      const mIdx = parseInt(month, 10) - 1
      const monthName = months[mIdx] || month
      
      let hour = parseInt(hourStr, 10)
      const ampm = hour >= 12 ? 'PM' : 'AM'
      hour = hour % 12
      hour = hour ? hour : 12
      
      return `${monthName} ${day}, ${year} at ${hour}:${minStr} ${ampm}`
    }
  }
  return sessionId
}

export function HistoryDashboard({ setActiveTab }) {
  const [sessions, setSessions] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [selectedPreview, setSelectedPreview] = useState(null)
  const [previewContent, setPreviewContent] = useState('')
  const [activePageIndex, setActivePageIndex] = useState(0)
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [reviewGranularity, setReviewGranularity] = useState('submodule')

  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const LIMIT = 10

  // Resume states
  const [resumingSessionId, setResumingSessionId] = useState(null)

  useEffect(() => {
    fetch(`/api/sessions?offset=0&limit=${LIMIT}`)
      .then((res) => res.json())
      .then((data) => {
        setSessions(data.sessions || [])
        setHasMore(data.has_more || false)
        setOffset(LIMIT)
        setLoading(false)
      })
      .catch((err) => {
        console.error('Failed to load history:', err)
        setLoading(false)
      })
  }, [])

  const handleLoadMore = () => {
    if (loadingMore) return
    setLoadingMore(true)
    fetch(`/api/sessions?offset=${offset}&limit=${LIMIT}`)
      .then((res) => res.json())
      .then((data) => {
        setSessions(prev => [...prev, ...(data.sessions || [])])
        setHasMore(data.has_more || false)
        setOffset(prev => prev + LIMIT)
        setLoadingMore(false)
      })
      .catch((err) => {
        console.error('Failed to load more history:', err)
        setLoadingMore(false)
      })
  }

  const handleLoadPreview = (sessionId) => {
    setSelectedPreview(sessionId)
    setPreviewContent('Loading preview...')
    setActivePageIndex(0)
    setIsDropdownOpen(false)
    fetch(`/api/sessions/${sessionId}/preview`)
      .then((res) => res.json())
      .then((data) => {
        setPreviewContent(data.content || '*No content available or generation incomplete.*')
      })
      .catch((err) => {
        setPreviewContent(`Failed to load textbook preview: ${err.message}`)
      })
  }

  const handleResumePipeline = async (sessionId) => {
    setResumingSessionId(sessionId)
    try {
      const fd = new FormData()
      fd.append('resume', 'true')
      fd.append('session_id', sessionId)
      
      const res = await fetch('/api/start', {
        method: 'POST',
        body: fd
      })
      const data = await res.json()
      if (!res.ok) {
        alert(data.detail || 'Failed to resume pipeline.')
      } else {
        // Redirect to Textbook Preview tab
        setActiveTab?.('preview')
      }
    } catch (err) {
      console.error(err)
      alert('Error initiating resume.')
    } finally {
      setResumingSessionId(null)
    }
  }

  const filteredSessions = sessions.filter((s) => {
    const name = (s.metadata?.session_name || s.metadata?.course_name || s.session_id).toLowerCase()
    const theme = (s.metadata?.prompt_theme || '').toLowerCase()
    const query = searchQuery.toLowerCase()
    return name.includes(query) || theme.includes(query)
  })

  // Get active session meta details during preview
  const activeSessionMeta = selectedPreview 
    ? (sessions.find(s => s.session_id === selectedPreview)?.metadata || {})
    : {}

  if (selectedPreview) {
    const submodules = parseSubmodules(previewContent)
    const activeSubmodule = submodules[activePageIndex] || { title: 'Unknown', content: '' }

    let displayedContent = activeSubmodule.content
    if (reviewGranularity === 'module' && submodules.length > 0) {
      const activeModIdx = activeSubmodule.moduleIndex || 1
      const modSubs = submodules.filter(s => s.moduleIndex === activeModIdx && s.id !== 'toc')
      if (modSubs.length > 0) {
        displayedContent = modSubs.map(s => s.content).join('\n\n---\n\n')
      }
    }

    return (
      <div className="w-full h-full flex flex-col bg-zinc-950">
        <div className="flex-shrink-0 flex items-center justify-between border-b border-zinc-800 px-8 h-14 bg-zinc-900/50">
          <div className="flex items-center gap-3">
            <span className="text-zinc-500 text-xs font-mono">{selectedPreview}</span>
            <ChevronRight className="w-4 h-4 text-zinc-600" />
            <span className="text-zinc-200 text-sm font-semibold">Textbook Preview</span>

            {/* Custom Premium Dropdown Selector */}
            {submodules.length > 1 && (
              <div className="relative ml-4 flex items-center gap-2 border-l border-zinc-800 pl-4">
                {/* Granularity mode toggle */}
                <div className="flex items-center bg-zinc-900 border border-zinc-800 rounded-lg p-0.5 text-[11px] font-medium">
                  <button
                    onClick={() => setReviewGranularity('submodule')}
                    className={`px-2 py-1 rounded-md transition-colors ${reviewGranularity === 'submodule' ? 'bg-zinc-800 text-emerald-400 font-semibold shadow-sm' : 'text-zinc-400 hover:text-zinc-200'}`}
                  >
                    Submodule
                  </button>
                  <button
                    onClick={() => setReviewGranularity('module')}
                    className={`px-2 py-1 rounded-md transition-colors ${reviewGranularity === 'module' ? 'bg-zinc-800 text-emerald-400 font-semibold shadow-sm' : 'text-zinc-400 hover:text-zinc-200'}`}
                  >
                    Full Module
                  </button>
                </div>

                <button
                  onClick={() => setActivePageIndex(prev => Math.max(0, prev - 1))}
                  disabled={activePageIndex === 0}
                  className="p-1 hover:bg-zinc-800 rounded text-zinc-400 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
                  title="Previous Submodule"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>

                <div className="relative">
                  <button
                    onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                    className="flex items-center justify-between gap-2 px-3 py-1 text-xs font-medium text-zinc-300 bg-zinc-900 border border-zinc-800 rounded-lg hover:bg-zinc-850 hover:text-zinc-100 transition-all select-none min-w-[210px] max-w-[320px]"
                  >
                    <span className="truncate">
                      {reviewGranularity === 'module'
                        ? `📁 ${activeSubmodule.moduleTitle || 'Module'} (Chapter View)`
                        : activeSubmodule.title}
                    </span>
                    <ChevronDown className={`w-3.5 h-3.5 text-zinc-500 transition-transform duration-200 ${isDropdownOpen ? 'rotate-180' : ''}`} />
                  </button>

                  {isDropdownOpen && (
                    <>
                      <div className="fixed inset-0 z-40" onClick={() => setIsDropdownOpen(false)} />
                      <div className="absolute left-0 mt-1.5 w-80 max-h-80 overflow-y-auto bg-zinc-950 border border-zinc-800/80 rounded-xl shadow-2xl z-50 p-2 backdrop-blur-md custom-scrollbar origin-top animate-in fade-in slide-in-from-top-1 duration-100">
                        {Object.entries(
                          submodules.reduce((acc, sub, idx) => {
                            const groupKey = sub.moduleTitle || 'Introduction';
                            if (!acc[groupKey]) acc[groupKey] = [];
                            acc[groupKey].push({ sub, idx });
                            return acc;
                          }, {})
                        ).map(([modTitle, items]) => (
                          <div key={modTitle} className="mb-2 last:mb-0">
                            <div className="px-2 py-1 text-[10px] font-bold text-zinc-500 uppercase tracking-wider bg-zinc-900/50 rounded mb-1 font-mono flex items-center gap-1.5">
                              <span>📁</span> {modTitle}
                            </div>
                            {items.map(({ sub, idx }) => (
                              <button
                                key={sub.id}
                                onClick={() => {
                                  setActivePageIndex(idx)
                                  setIsDropdownOpen(false)
                                }}
                                className={`w-full text-left px-3 py-1.5 text-xs rounded-lg transition-colors flex items-center justify-between ${idx === activePageIndex ? 'bg-emerald-500/10 text-emerald-400 font-semibold' : 'text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200'}`}
                              >
                                <span className="truncate pl-2 font-sans">{sub.title}</span>
                                {idx === activePageIndex && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0 ml-2" />}
                              </button>
                            ))}
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </div>
                <button
                  onClick={() => setActivePageIndex(prev => Math.min(submodules.length - 1, prev + 1))}
                  disabled={activePageIndex === submodules.length - 1}
                  className="p-1 hover:bg-zinc-800 rounded text-zinc-400 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
                  title="Next Submodule"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
          <div className="flex items-center gap-3">
            {activeSessionMeta.status !== 'Completed' && (
              <button
                onClick={() => handleResumePipeline(selectedPreview)}
                disabled={resumingSessionId === selectedPreview}
                className="text-xs bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-semibold px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 active:scale-[0.97]"
              >
                {resumingSessionId === selectedPreview ? (
                  <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Resuming…</>
                ) : (
                  <><Play className="w-3.5 h-3.5 fill-current" /> Resume Pipeline</>
                )}
              </button>
            )}
            <button
              onClick={() => setSelectedPreview(null)}
              className="text-xs bg-zinc-800 hover:bg-zinc-750 text-zinc-300 px-3 py-1.5 rounded-lg border border-zinc-700/50 transition-colors"
            >
              Back to History
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-auto p-8 custom-scrollbar">
          <div className="max-w-4xl mx-auto">
            <pre className="whitespace-pre-wrap font-mono text-xs text-zinc-300 bg-zinc-900/30 p-6 rounded-xl border border-zinc-800/50 leading-relaxed shadow-inner">
              {displayedContent}
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
          <p className="text-xs text-zinc-500 mt-1">Browse, inspect, and resume past generation runs.</p>
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
        <>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredSessions.map((s) => {
            const metadata = s.metadata || {}
            const pct = Math.min(100, Math.max(0, metadata.completion_rate || 0))
            
            const customName = metadata.session_name || ''
            const cleanName = customName || metadata.course_name || s.session_id
            const isCompleted = metadata.status === 'Completed'
            const status = metadata.status || 'Unknown'

            // Format status badge design
            let statusText = status
            let badgeStyle = 'border-zinc-800 bg-zinc-950 text-zinc-400'
            if (status === 'Completed') {
              statusText = 'Completed'
              badgeStyle = 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400'
            } else if (status === 'Running') {
              statusText = 'Running'
              badgeStyle = 'border-teal-500/20 bg-teal-500/10 text-teal-400 animate-pulse'
            } else if (status === 'paused_for_repair') {
              statusText = 'Paused - Action Required'
              badgeStyle = 'border-amber-500/20 bg-amber-500/10 text-amber-400'
            } else if (status === 'paused_for_review') {
              statusText = 'Paused - Review Gate'
              badgeStyle = 'border-blue-500/20 bg-blue-500/10 text-blue-400'
            } else if (status === 'Stopped') {
              statusText = 'Stopped'
              badgeStyle = 'border-zinc-800 bg-zinc-900/50 text-zinc-500'
            }

            const dateStr = formatSessionDate(s.session_id)

            return (
              <div
                key={s.session_id}
                className="flex flex-col bg-zinc-900/30 border border-zinc-800/80 rounded-2xl p-6 gap-4 hover:border-zinc-700/50 hover:bg-zinc-900/50 transition-all shadow-[0_4px_20px_-10px_rgba(0,0,0,0.5)]"
              >
                <div className="flex flex-col gap-1.5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-center justify-between gap-2 flex-1 min-w-0 group">
                      <h3 className="font-semibold text-zinc-200 text-sm tracking-tight truncate" title={cleanName}>
                        {cleanName}
                      </h3>
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px] text-zinc-500 font-mono flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-zinc-600" />
                      {dateStr}
                    </span>
                    <Badge variant="outline" className={`text-[9px] uppercase tracking-wider font-semibold py-0.5 px-2 rounded-full ${badgeStyle}`}>
                      {statusText}
                    </Badge>
                  </div>
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
                    <BookOpen className="w-3.5 h-3.5 text-zinc-400" />
                    Inspect Textbook
                  </button>
                  {!isCompleted && (
                    <button
                      onClick={() => handleResumePipeline(s.session_id)}
                      disabled={resumingSessionId === s.session_id}
                      className="text-[11px] font-semibold bg-emerald-600/10 hover:bg-emerald-600 text-emerald-400 hover:text-white py-2 px-3.5 rounded-lg border border-emerald-500/20 hover:border-emerald-500 transition-all flex items-center justify-center gap-1.5 active:scale-[0.97]"
                      title="Resume compilation loop"
                    >
                      {resumingSessionId === s.session_id ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Play className="w-3.5 h-3.5 fill-current" />
                      )}
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
        
        {hasMore && (
          <div className="flex justify-center mt-6">
            <button
              onClick={handleLoadMore}
              disabled={loadingMore}
              className="flex items-center gap-2 px-6 py-2.5 bg-zinc-900 border border-zinc-800 rounded-full text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100 transition-colors disabled:opacity-50 text-xs font-semibold tracking-wider"
            >
              {loadingMore && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {loadingMore ? 'LOADING...' : 'LOAD MORE'}
            </button>
          </div>
        )}
      </>
      )}
    </div>
  )
}
