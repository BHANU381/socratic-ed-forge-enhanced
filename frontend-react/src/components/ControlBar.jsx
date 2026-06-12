import { useState, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Settings2, Play, Square, Trash2, Upload, Loader2 } from 'lucide-react'

export function ControlBar({ isRunning, onStarted, onStopped, onCleared }) {
  const [file, setFile]         = useState(null)
  const [starting, setStarting] = useState(false)
  const [stopping, setStopping] = useState(false)
  const [error, setError]       = useState(null)
  const [rpm, setRpm]           = useState(15)
  const [tpm, setTpm]           = useState(250000)
  const fileInputRef            = useRef(null)

  async function handleStart() {
    if (!file) { setError('Please select a JSON config file first.'); return }
    setError(null)
    setStarting(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('rpm_limit', rpm.toString())
      fd.append('tpm_limit', tpm.toString())
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
    <Card className="bg-card border-border/50 shadow-lg relative">
      <CardHeader className="pb-3 pt-4 px-4">
        <CardTitle className="text-[0.7rem] font-bold tracking-widest text-muted-foreground uppercase flex items-center gap-2">
          <Settings2 className="w-3.5 h-3.5" />
          Controls
        </CardTitle>
      </CardHeader>
      
      <CardContent className="px-4 pb-4 space-y-2">
        {!isRunning && (
          <>
            <label
              className={`flex items-center justify-center border border-dashed rounded-md p-2.5 text-xs font-medium cursor-pointer transition-colors ${
                file 
                  ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20' 
                  : 'border-border/60 bg-muted/20 text-muted-foreground hover:border-indigo-400 hover:text-indigo-400'
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
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">RPM Limit</label>
                <input 
                  type="number" 
                  value={rpm} 
                  onChange={e => setRpm(e.target.value)}
                  className="flex h-8 w-full rounded-md border border-border/60 bg-muted/20 px-3 py-1 text-xs shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-indigo-500"
                />
              </div>
              <div className="flex-1 flex flex-col gap-1">
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">TPM Limit</label>
                <input 
                  type="number" 
                  value={tpm} 
                  onChange={e => setTpm(e.target.value)}
                  className="flex h-8 w-full rounded-md border border-border/60 bg-muted/20 px-3 py-1 text-xs shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-indigo-500"
                />
              </div>
            </div>

            <Button 
              className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-lg shadow-indigo-500/25 transition-all"
              onClick={handleStart}
              disabled={!file || starting}
            >
              {starting ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Launching…</>
              ) : (
                <><Play className="mr-2 h-4 w-4 fill-current" /> Start Production</>
              )}
            </Button>
          </>
        )}

        {isRunning && (
          <Button 
            variant="destructive"
            className="w-full bg-red-600 hover:bg-red-700 shadow-lg shadow-red-600/30 transition-all font-semibold animate-pulse hover:animate-none"
            onClick={handleStop}
            disabled={stopping}
            title="Stops token spending immediately"
          >
            {stopping ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Stopping…</>
            ) : (
              <><Square className="mr-2 h-4 w-4 fill-current" /> Stop Loop (Kill All)</>
            )}
          </Button>
        )}

        <Button 
          variant="outline" 
          className="w-full border-border/50 bg-muted/20 hover:bg-muted text-muted-foreground text-xs" 
          onClick={handleClear}
        >
          <Trash2 className="mr-2 h-3.5 w-3.5" /> Clear Logs & Reset
        </Button>

        {error && (
          <div className="text-xs text-red-400 mt-2 p-1 font-medium flex items-start gap-1">
            <span className="mt-0.5">⚠</span> {error}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
