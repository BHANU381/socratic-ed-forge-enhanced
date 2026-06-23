import { useState, useRef, useEffect } from 'react'
import { Settings2, Play, Square, Trash2, Upload, Loader2 } from 'lucide-react'

export function ControlBar({ isRunning, onStarted, onStopped, onCleared }) {
  const [file, setFile]         = useState(null)
  const [starting, setStarting] = useState(false)
  const [stopping, setStopping] = useState(false)
  const [error, setError]       = useState(null)
  const [rpm, setRpm]           = useState(15)
  const [tpm, setTpm]           = useState(250000)
  const [themes, setThemes]     = useState(["default"])
  const [selectedTheme, setSelectedTheme] = useState("default")
  const [learnerLevel, setLearnerLevel] = useState("beginner")
  const [codeStyle, setCodeStyle]       = useState("progressive_production")
  const [expDepth, setExpDepth]         = useState("balanced")
  const [qualityProfile, setQualityProfile] = useState("standard")
  const [resume, setResume]             = useState(false)
  const fileInputRef            = useRef(null)

  useEffect(() => {
    async function fetchThemes() {
      try {
        const res = await fetch('/api/prompt-themes')
        if (res.ok) {
          const data = await res.json()
          setThemes(data.themes || ["default"])
        }
      } catch (e) {
        console.error("Failed to load themes:", e)
      }
    }
    fetchThemes()
  }, [])

  async function handleStart() {
    if (!file) { setError('Please select a JSON config file first.'); return }
    setError(null)
    setStarting(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('rpm_limit', rpm.toString())
      fd.append('tpm_limit', tpm.toString())
      fd.append('prompt_theme', selectedTheme)
      fd.append('learner_level', learnerLevel)
      fd.append('code_example_style', codeStyle)
      fd.append('explanation_depth', expDepth)
      fd.append('quality_profile', qualityProfile)
      fd.append('resume', resume.toString())
      const res = await fetch('/api/start', { method: 'POST', body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Start failed')
      setFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      onStarted?.()
    } catch (e) {
      setError(e.message)
    } finally {
      setStarting(false)
    }
  }

  async function handleStop() {
    setStopping(true)
    setError(null)
    try {
      const res = await fetch('/api/stop', { method: 'POST' })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Stop failed')
      onStopped?.()
    } catch (e) {
      setError(e.message)
    } finally {
      setTimeout(() => setStopping(false), 2000)
    }
  }

  async function handleClear() {
    await fetch('/api/logs', { method: 'DELETE' })
    onCleared?.()
  }

  return (
    <div className="flex flex-col p-8 gap-5 shrink-0">
      <div className="flex items-center justify-between">
        <h3 className="text-[10px] font-semibold tracking-widest text-zinc-500 uppercase flex items-center gap-2">
          <Settings2 className="w-3.5 h-3.5" />
          Controls
        </h3>
      </div>
      
      <div className="flex flex-col gap-4">
        {!isRunning && (
          <>
            <label
              className={`flex items-center justify-center border border-dashed rounded-md p-2.5 text-xs font-medium cursor-pointer transition-colors ${
                file 
                  ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20' 
                  : 'border-border/60 bg-muted/20 text-muted-foreground hover:border-zinc-400 hover:text-zinc-300'
              }`}
              htmlFor="json-upload"
            >
              {file ? (
                <span className="truncate max-w-[200px]">✓ {file.name}</span>
              ) : (
                <span className="flex items-center gap-1.5"><Upload className="w-3.5 h-3.5" /> Click to upload JSON config</span>
              )}
            </label>
            <input
              id="json-upload"
              ref={fileInputRef}
              type="file"
              accept=".json"
              className="hidden"
              onChange={e => { setFile(e.target.files[0]); setError(null) }}
            />

            <div className="flex gap-2 w-full">
              <div className="flex-1 flex flex-col gap-1">
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Prompt Theme</label>
                <select
                  value={selectedTheme}
                  onChange={e => setSelectedTheme(e.target.value)}
                  className="flex h-8 w-full rounded border border-zinc-800 bg-zinc-900/50 px-3 py-1 text-xs shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-zinc-500 text-zinc-200"
                >
                  {themes.map(t => (
                    <option key={t} value={t} className="bg-zinc-900 text-zinc-200">{t}</option>
                  ))}
                </select>
              </div>
              <div className="flex flex-1 gap-2">
                <div className="flex-1 flex flex-col gap-1">
                  <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">RPM</label>
                  <input 
                    type="number" 
                    min="1"
                    value={rpm} 
                    onChange={e => setRpm(e.target.value)}
                    onKeyDown={(e) => {
                      if (['-', '+', 'e', 'E', '.'].includes(e.key)) e.preventDefault();
                    }}
                    className="flex h-8 w-full rounded-md border border-border/60 bg-muted/20 px-3 py-1 text-xs shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-zinc-500"
                  />
                </div>
                <div className="flex-1 flex flex-col gap-1">
                  <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">TPM</label>
                  <input 
                    type="number" 
                    min="1"
                    value={tpm} 
                    onChange={e => setTpm(e.target.value)}
                    onKeyDown={(e) => {
                      if (['-', '+', 'e', 'E', '.'].includes(e.key)) e.preventDefault();
                    }}
                    className="flex h-8 w-full rounded-md border border-border/60 bg-muted/20 px-3 py-1 text-xs shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-zinc-500"
                  />
                </div>
              </div>
            </div>

            <div className="flex gap-2 w-full">
              <div className="flex-1 flex flex-col gap-1">
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Learner Level</label>
                <select
                  value={learnerLevel}
                  onChange={e => setLearnerLevel(e.target.value)}
                  className="flex h-8 w-full rounded border border-zinc-800 bg-zinc-900/50 px-3 py-1 text-xs shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-zinc-500 text-zinc-200"
                >
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </div>
              <div className="flex-1 flex flex-col gap-1">
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Code Style</label>
                <select
                  value={codeStyle}
                  onChange={e => setCodeStyle(e.target.value)}
                  className="flex h-8 w-full rounded border border-zinc-800 bg-zinc-900/50 px-3 py-1 text-xs shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-zinc-500 text-zinc-200"
                >
                  <option value="progressive_production">Progressive Prod</option>
                  <option value="minimal">Minimal</option>
                  <option value="practical">Practical</option>
                  <option value="production_first">Production First</option>
                </select>
              </div>
            </div>

            <div className="flex gap-2 w-full">
              <div className="flex-1 flex flex-col gap-1">
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Exp. Depth</label>
                <select
                  value={expDepth}
                  onChange={e => setExpDepth(e.target.value)}
                  className="flex h-8 w-full rounded border border-zinc-800 bg-zinc-900/50 px-3 py-1 text-xs shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-zinc-500 text-zinc-200"
                >
                  <option value="balanced">Balanced</option>
                  <option value="concise">Concise</option>
                  <option value="deep">Deep</option>
                </select>
              </div>
              <div className="flex-1 flex flex-col gap-1">
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Quality Profile</label>
                <select
                  value={qualityProfile}
                  onChange={e => setQualityProfile(e.target.value)}
                  className="flex h-8 w-full rounded border border-zinc-800 bg-zinc-900/50 px-3 py-1 text-xs shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-zinc-500 text-zinc-200"
                >
                  <option value="standard">Standard</option>
                  <option value="light">Light</option>
                  <option value="textbook">Textbook</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-2 mt-1">
              <input
                id="resume-checkbox"
                type="checkbox"
                checked={resume}
                onChange={e => setResume(e.target.checked)}
                className="rounded border-zinc-800 bg-zinc-900/50 text-zinc-200 focus:ring-zinc-500 h-3.5 w-3.5"
              />
              <label htmlFor="resume-checkbox" className="text-xs text-muted-foreground cursor-pointer select-none">
                Resume from last incomplete session
              </label>
            </div>

            <button 
              className="w-full bg-zinc-100 text-zinc-900 hover:bg-white shadow-[0_2px_10px_-3px_rgba(255,255,255,0.1)] transition-all font-semibold tracking-wide text-xs py-2.5 rounded flex items-center justify-center active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={handleStart}
              disabled={!file || starting}
            >
              {starting ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Launching…</>
              ) : (
                <><Play className="mr-2 h-4 w-4 fill-current" /> Start Production</>
              )}
            </button>
          </>
        )}

        {isRunning && (
          <button 
            className="w-full bg-rose-600 hover:bg-rose-500 text-white shadow-[0_2px_10px_-3px_rgba(225,29,72,0.3)] transition-all font-semibold tracking-wide text-xs py-2.5 rounded flex items-center justify-center animate-pulse hover:animate-none active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={handleStop}
            disabled={stopping}
            title="Stops token spending immediately"
          >
            {stopping ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Stopping…</>
            ) : (
              <><Square className="mr-2 h-4 w-4 fill-current" /> Stop Loop (Kill All)</>
            )}
          </button>
        )}

        <button 
          className="w-full border border-zinc-800/80 bg-zinc-900/30 hover:bg-zinc-800 text-zinc-400 text-[10px] uppercase tracking-widest font-semibold py-2 rounded transition-all flex items-center justify-center active:scale-[0.98]" 
          onClick={handleClear}
        >
          <Trash2 className="mr-2 h-3.5 w-3.5" /> Clear Logs & Reset
        </button>

        {error && (
          <div className="text-xs text-red-400 mt-2 p-1 font-medium flex items-start gap-1">
            <span className="mt-0.5">⚠</span> {error}
          </div>
        )}
      </div>
    </div>
  )
}
