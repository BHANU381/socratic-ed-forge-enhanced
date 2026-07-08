import React from 'react'

export function PipelineMatrix({ telemetry }) {
  const courseStructure = telemetry?.course_structure || []
  const submoduleTelemetry = telemetry?.submodule_telemetry || {}

  const renderBadge = (val) => {
    if (val === '1' || val === '2' || val === '3') {
      return (
        <span className="inline-flex items-center justify-center px-3 py-1 rounded-md text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-sm font-mono tracking-wide">
          Pass (att. {val})
        </span>
      )
    }
    if (val === 'F') {
      return (
        <span className="inline-flex items-center justify-center px-3 py-1 rounded-md text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20 shadow-sm font-mono tracking-wide">
          FAIL
        </span>
      )
    }
    return (
      <span className="inline-flex items-center justify-center px-3 py-1 rounded-md text-[10px] font-semibold bg-zinc-900/50 text-zinc-500 border border-zinc-800 font-mono tracking-wide">
        —
      </span>
    )
  }

  if (courseStructure.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[50vh] p-8 text-center bg-zinc-950 border border-zinc-800/40 rounded-2xl">
        <div className="w-12 h-12 flex items-center justify-center rounded-xl bg-zinc-900 border border-zinc-800 text-zinc-500 mb-4">
          📊
        </div>
        <h4 className="text-sm font-semibold text-zinc-300 mb-1">Pipeline Matrix Idle</h4>
        <p className="text-xs text-zinc-500 max-w-sm">
          Once you upload a JSON configuration and start the generation pipeline, a detailed matrix of validation checks will appear here.
        </p>
      </div>
    )
  }

  return (
    <div className="w-full flex flex-col gap-6">
      <div className="flex flex-col gap-1.5">
        <h3 className="text-lg font-semibold text-zinc-200 tracking-tight">Validation Check Matrix</h3>
        <p className="text-xs text-zinc-500">
          Tracks the number of attempt/patch loops taken by each validation agent before passing or marking a failure.
        </p>
      </div>

      <div className="w-full border border-zinc-800/50 rounded-2xl overflow-hidden bg-zinc-950/40 backdrop-blur-md">
        <table className="w-full border-collapse text-left text-xs">
          <thead>
            <tr className="border-b border-zinc-800/50 bg-zinc-900/40 text-zinc-400 font-medium">
              <th className="p-4 w-[36%]">Module / Submodule</th>
              <th className="p-4 text-center w-[16%]">Deterministic Validator</th>
              <th className="p-4 text-center w-[16%]">Grounding Auditor</th>
              <th className="p-4 text-center w-[16%]">Semantic Evaluator</th>
              <th className="p-4 text-center w-[16%]">Analogy Agent</th>
            </tr>
          </thead>
          <tbody>
            {courseStructure.map((mod, modIdx) => {
              const modTitle = mod.module_title || `Module ${modIdx + 1}`
              const submodules = mod.submodules || []

              return (
                <React.Fragment key={modIdx}>
                  {/* Module Group Row */}
                  <tr className="bg-zinc-900/20 border-b border-zinc-800/30">
                    <td colSpan={5} className="p-3 font-semibold text-zinc-300 bg-zinc-900/10 font-sans tracking-wide">
                      📁 {modTitle}
                    </td>
                  </tr>

                  {/* Submodule Rows */}
                  {submodules.map((sub, subIdx) => {
                    const isRowPaused = telemetry?.status === 'paused_for_repair' && telemetry?.current_submodule === sub
                    const sessionId = telemetry?.session_dir?.split(/[\\/]/).pop() || ''
                    const stats = submoduleTelemetry[modTitle]?.[sub] || {}
                    const det = stats.deterministic || '-'
                    const gro = stats.grounding || '-'
                    const sem = stats.semantic || '-'
                    const ana = stats.analogy || '-'

                    return (
                      <React.Fragment key={subIdx}>
                        <tr 
                          className="border-b border-zinc-800/30 hover:bg-zinc-900/10 transition-colors"
                        >
                          <td className="p-4 pl-8 text-zinc-400 font-medium leading-relaxed">
                            📄 {sub}
                          </td>
                          <td className="p-4 text-center">
                            {renderBadge(det)}
                          </td>
                          <td className="p-4 text-center">
                            {renderBadge(gro)}
                          </td>
                          <td className="p-4 text-center">
                            {renderBadge(sem)}
                          </td>
                          <td className="p-4 text-center">
                            {renderBadge(ana)}
                          </td>
                        </tr>
                        {isRowPaused && (
                          <tr className="bg-amber-500/[0.02]">
                            <td colSpan={5} className="p-6 border-b border-zinc-800/80 bg-zinc-900/10">
                              <div className="flex flex-col gap-4 max-w-3xl">
                                <div className="flex items-center gap-2 text-xs font-bold text-amber-400 uppercase tracking-wider">
                                  ⚠️ Active Validation Blockers Detected
                                </div>
                                <ul className="text-xs text-zinc-300 space-y-1.5 list-disc list-inside bg-zinc-950 p-4 rounded-xl border border-zinc-800/50">
                                  {telemetry.failure_reasons?.filter(r => r.severity === 'blocker').map((b, idx) => (
                                    <li key={idx}>{b.message}</li>
                                  )) || <li className="italic text-zinc-500">Validation issues reported.</li>}
                                </ul>
                                <div className="flex gap-2">
                                  <input
                                    type="text"
                                    placeholder="Instruct Patch Editor to repair (e.g. 'Use AWS instead')..."
                                    id={`repair-input-${subIdx}`}
                                    className="flex-1 bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-2 text-xs text-zinc-300 placeholder-zinc-600 focus:outline-none focus:border-zinc-700"
                                  />
                                  <button
                                    onClick={async () => {
                                      const inputVal = document.getElementById(`repair-input-${subIdx}`)?.value || '';
                                      if (!sessionId) return;
                                      
                                      await fetch('/api/sessions/edit', {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({
                                          session_id: sessionId,
                                          submodule_filename: 'breakpoint.json',
                                          content: JSON.stringify({
                                            status: 'resolved',
                                            resolution: 'retry',
                                            user_instructions: inputVal
                                          })
                                        })
                                      });
                                    }}
                                    className="text-xs font-semibold bg-emerald-500 hover:bg-emerald-600 text-zinc-950 px-4 py-2 rounded-xl transition-colors"
                                  >
                                    Submit Repair
                                  </button>
                                  <button
                                    onClick={async () => {
                                      if (!sessionId) return;
                                      await fetch('/api/sessions/edit', {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({
                                          session_id: sessionId,
                                          submodule_filename: 'breakpoint.json',
                                          content: JSON.stringify({
                                            status: 'resolved',
                                            resolution: 'force_approve',
                                            user_instructions: ''
                                          })
                                        })
                                      });
                                    }}
                                    className="text-xs font-semibold bg-zinc-800 hover:bg-zinc-750 text-zinc-300 border border-zinc-750/50 px-4 py-2 rounded-xl transition-colors"
                                  >
                                    Force Pass
                                  </button>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    )
                  })}
                </React.Fragment>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
