import { useRef, memo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { BookOpen } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

export const PreviewPanel = memo(function PreviewPanel({ preview, isLive }) {
  const containerRef = useRef(null)

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
    <div className="flex flex-col h-full bg-zinc-950 text-zinc-50 min-w-0 min-h-0 w-full">
      <div className="flex items-center gap-3 px-8 py-4 border-b border-zinc-800/50 bg-zinc-950/80 shrink-0 backdrop-blur-xl sticky top-0 z-10 shadow-sm">
        <BookOpen className="w-4 h-4 text-zinc-400" />
        <h2 className="text-sm font-semibold text-zinc-200 tracking-wide">Live Book Preview</h2>
        {isLive && (
          <Badge variant="outline" className="ml-2 bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[10px] tracking-widest px-2.5 py-0 h-5 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse mr-1.5 inline-block" />
            LIVE DRAFT
          </Badge>
        )}
      </div>

      <div className="flex-1 overflow-auto px-12 py-12 scroll-smooth min-h-0 min-w-0 custom-scrollbar" ref={containerRef}>
        <div className="max-w-4xl mx-auto prose prose-invert prose-zinc">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {preview}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  )
})
