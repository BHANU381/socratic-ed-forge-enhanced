import { useRef, memo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { BookOpen } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

export const PreviewPanel = memo(function PreviewPanel({ preview, isLive }) {
  const containerRef = useRef(null)

  if (!preview) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground italic gap-4 h-full bg-background">
        <div className="flex gap-1.5">
          <span className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" style={{ animationDelay: '0s' }} />
          <span className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" style={{ animationDelay: '0.2s' }} />
          <span className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" style={{ animationDelay: '0.4s' }} />
        </div>
        Waiting for production to start…
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-transparent text-foreground min-w-0 min-h-0 w-full">
      <div className="flex items-center gap-3 px-8 py-3 border-b border-border/40 bg-black/20 shrink-0 backdrop-blur-sm sticky top-0 z-10">
        <BookOpen className="w-4 h-4 text-indigo-400" />
        <h2 className="text-sm font-semibold text-secondary-foreground tracking-wide">Live Book Preview</h2>
        {isLive && (
          <Badge variant="outline" className="ml-2 bg-purple-500/10 text-purple-400 border-purple-500/20 text-[0.65rem] tracking-widest px-2 py-0 h-5">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-500 animate-pulse mr-1.5 inline-block" />
            LIVE DRAFT
          </Badge>
        )}
      </div>

      <div className="flex-1 overflow-auto px-12 py-8 scroll-smooth min-h-0 min-w-0" ref={containerRef}>
        <div className="max-w-4xl mx-auto prose prose-invert">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {preview}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  )
})
