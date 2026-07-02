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
              <th className="p-4 w-[40%]">Module / Submodule</th>
              <th className="p-4 text-center w-[20%]">Deterministic Validator</th>
              <th className="p-4 text-center w-[20%]">Grounding Auditor</th>
              <th className="p-4 text-center w-[20%]">Semantic Evaluator</th>
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
                    <td colSpan={4} className="p-3 font-semibold text-zinc-300 bg-zinc-900/10 font-sans tracking-wide">
                      📁 {modTitle}
                    </td>
                  </tr>

                  {/* Submodule Rows */}
                  {submodules.map((sub, subIdx) => {
                    const stats = submoduleTelemetry[modTitle]?.[sub] || {}
                    const det = stats.deterministic || '-'
                    const gro = stats.grounding || '-'
                    const sem = stats.semantic || '-'

                    return (
                      <tr 
                        key={subIdx} 
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
                      </tr>
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
