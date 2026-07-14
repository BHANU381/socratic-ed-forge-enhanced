import { useState, useRef, useEffect, useLayoutEffect, useCallback, memo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { BookOpen, Edit3, Save, MessageSquare, X, CheckCircle, AlertTriangle, ArrowRight, Copy, Sparkles, Check, ArrowLeft } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

const CodeBlock = ({ className, children }) => {
  const [copied, setCopied] = useState(false)
  const match = /language-(\w+)/.exec(className || '')
  const lang = match ? match[1] : 'text'
  const codeText = String(children).replace(/\n$/, '')

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(codeText)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy code text', err)
    }
  }

  return (
    <div className="relative border border-zinc-800 rounded-xl overflow-hidden my-4 bg-zinc-950 shadow-lg">
      <div className="flex items-center justify-between px-4 py-2 bg-zinc-900 border-b border-zinc-850 text-xs text-zinc-400 font-mono select-none">
        <span>{lang}</span>
        <button
          onClick={handleCopy}
          className="hover:text-zinc-250 transition-colors flex items-center gap-1.5 active:scale-95 duration-100"
        >
          {copied ? (
            <>
              <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-[10px] text-emerald-400 font-sans">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span className="text-[10px] font-sans">Copy code</span>
            </>
          )}
        </button>
      </div>
      <pre className="p-4 overflow-x-auto text-xs leading-relaxed font-mono text-zinc-300 bg-zinc-950/80 custom-scrollbar">
        <code className={className}>{children}</code>
      </pre>
    </div>
  )
}

const markdownComponents = {
  code({ node, inline, className, children, ...props }) {
    if (!inline) {
      return <CodeBlock className={className} {...props}>{children}</CodeBlock>
    }
    return (
      <code className="bg-zinc-800 text-amber-300 px-1.5 py-0.5 rounded text-[11px] font-mono border border-zinc-750/60" {...props}>
        {children}
      </code>
    )
  },
  p: ({ children }) => {
    // Custom inline highlighting for staged edits
    if (typeof children !== 'string') return <p className="leading-relaxed text-zinc-300 text-sm mb-4">{children}</p>;
    
    // Check if any active queued edit is inside this paragraph
    let contentStr = children;
    return (
      <p className="leading-relaxed text-zinc-300 text-sm mb-4 relative">
        {contentStr}
      </p>
    );
  }
}

const _get_containing_paragraph = (fullText, selectedText) => {
  if (!fullText || !selectedText) return selectedText;
  const idx = fullText.indexOf(selectedText);
  if (idx === -1) return selectedText;
  
  const precedingText = fullText.slice(0, idx);
  const lastDoubleNewline = precedingText.lastIndexOf('\n\n');
  
  let lastHeading = -1;
  try {
    const headingMatches = [...precedingText.matchAll(/\n#+\s+/g)];
    if (headingMatches.length > 0) {
      lastHeading = headingMatches[headingMatches.length - 1].index;
    } else if (precedingText.startsWith('#')) {
      lastHeading = 0;
    }
  } catch (e) {}

  let lastBullet = -1;
  try {
    const bulletMatches = [...precedingText.matchAll(/\n\s*([-*]|\d+\.)\s+/g)];
    if (bulletMatches.length > 0) {
      lastBullet = bulletMatches[bulletMatches.length - 1].index;
    }
  } catch (e) {}

  let start = 0;
  if (lastDoubleNewline !== -1) start = lastDoubleNewline + 2;
  if (lastHeading !== -1 && lastHeading > lastDoubleNewline) {
    start = lastHeading;
  }
  if (lastBullet !== -1 && lastBullet > start) {
    start = lastBullet + 1;
  }

  const followingText = fullText.slice(idx + selectedText.length);
  const nextDoubleNewline = followingText.indexOf('\n\n');
  
  let nextHeading = -1;
  try {
    const headingMatch = followingText.match(/\n#+\s+/);
    if (headingMatch) {
      nextHeading = headingMatch.index;
    }
  } catch (e) {}

  let nextBullet = -1;
  try {
    const bulletMatch = followingText.match(/\n\s*([-*]|\d+\.)\s+/);
    if (bulletMatch) {
      nextBullet = bulletMatch.index;
    }
  } catch (e) {}

  let end = fullText.length;
  const candidates = [];
  if (nextDoubleNewline !== -1) candidates.push(idx + selectedText.length + nextDoubleNewline);
  if (nextHeading !== -1) candidates.push(idx + selectedText.length + nextHeading);
  if (nextBullet !== -1) candidates.push(idx + selectedText.length + nextBullet);
  
  if (candidates.length > 0) {
    end = Math.min(...candidates);
  }
  
  return fullText.slice(start, end).trim();
};

export const PreviewPanel = memo(function PreviewPanel({ preview, isLive, telemetry, isActive = true }) {
  const containerRef = useRef(null)
  const scrollPosRef = useRef(null)
  const lastRenderedContent = useRef(null)
  const prevStatusRef = useRef('')
  const [showCompletionBadge, setShowCompletionBadge] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [content, setRawContent] = useState(() => (preview || '').replace(/\r\n/g, '\n'))
  const [filename, setFilename] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const setContent = useCallback((val) => {
    if (typeof val === 'function') {
      setRawContent(prev => {
        const next = val(prev);
        return typeof next === 'string' ? next.replace(/\r\n/g, '\n') : next;
      });
    } else if (typeof val === 'string') {
      setRawContent(val.replace(/\r\n/g, '\n'));
    } else {
      setRawContent(val);
    }
  }, []);
  
  // Highlight selection states
  const [selectionRange, setSelectionRange] = useState(null)
  const [selectionCoords, setSelectionCoords] = useState({ top: 0, left: 0 })
  const [selectionRelativeCoords, setSelectionRelativeCoords] = useState({ top: 0, left: 0 })
  const [selectedText, setSelectedText] = useState('')
  const [showHighlightModal, setShowHighlightModal] = useState(false)
   const [replacementText, setReplacementText] = useState('')
  const [selectedMode, setSelectedMode] = useState(null) // 'sentence' | 'paragraph' | null
   const [isPopupVisible, setIsPopupVisible] = useState(true)
    const popupRef = useRef(null)

  const clearActiveSelection = () => {
    setSelectionRange(null)
    setSelectedText('')
    setSelectedMode(null)
    window.getSelection()?.removeAllRanges()
    if (typeof CSS !== 'undefined' && CSS.highlights) {
      CSS.highlights.delete("user-selection")
    }
  }

  // Sidebar chat states for recovery
  const [showChat, setShowChat] = useState(false)
  const [chatPrompt, setChatPrompt] = useState('')
  const [chatStatus, setChatStatus] = useState('')

  const getHighlightedMarkdown = (rawMarkdown) => {
    if (!rawMarkdown) return ''
    let processed = rawMarkdown

    // 1. Highlight queued edits with custom data tags and inline close buttons
    queuedEdits.forEach(edit => {
      if (!edit.originalText) return
      const escaped = edit.originalText.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&')
      const highlightSpan = `<span class="staged-highlight" data-instruction="Feedback: ${edit.instruction.replace(/"/g, '&quot;')}">${edit.originalText}<button class="remove-staged-btn" data-edit-id="${edit.id}">×</button></span>`
      try {
        const regex = new RegExp(escaped, 'g')
        processed = processed.replace(regex, highlightSpan)
      } catch (err) {
        // Fallback simple replace if RegExp fails
        processed = processed.replace(edit.originalText, highlightSpan)
      }
    })

    return processed
  }

  const sessionId = telemetry?.session_dir?.split(/[\\/]/).pop() || ''
  const isPaused = telemetry?.status === 'paused_for_repair'
  const isReviewing = telemetry?.status === 'paused_for_review'

  // Module review & Diff states
  const [isApproving, setIsApproving] = useState(false)
  const [aiInstruction, setAiInstruction] = useState('')
  const [activePatch, setActivePatch] = useState(null)
  const [critiqueText, setCritiqueText] = useState('')
  const [showAiModal, setShowAiModal] = useState(false)
  const [chatMessages, setChatMessages] = useState([])
  const [editScope, setEditScope] = useState('selection')
  const [isQueryingPatch, setIsQueryingPatch] = useState(false)
  const [chatLoading, setChatLoading] = useState(false)

  // Batch edit states
  const [queuedEdits, setQueuedEdits] = useState([])
  const [activeBatchPatches, setActiveBatchPatches] = useState([])
  const [batchInstruction, setBatchInstruction] = useState('')
  const [isProcessingBatch, setIsProcessingBatch] = useState(false)

  const saveScroll = useCallback(() => {
    if (containerRef.current) {
      scrollPosRef.current = containerRef.current.scrollTop
    }
  }, [])

  useLayoutEffect(() => {
    if (scrollPosRef.current !== null && containerRef.current) {
      containerRef.current.scrollTop = scrollPosRef.current
    }
  }, [content, queuedEdits, activeBatchPatches, activePatch])

  useEffect(() => {
    const prevStatus = prevStatusRef.current
    const currentStatus = telemetry?.status || ''
    
    if (prevStatus === 'Running' && currentStatus === 'Completed') {
      if (containerRef.current) {
        if (containerRef.current.scrollTop < 100) {
          containerRef.current.scrollTo({ top: 0, behavior: 'smooth' })
        } else {
          setShowCompletionBadge(true)
        }
      }
    } else if (currentStatus === 'Running') {
      setShowCompletionBadge(false)
    }
    prevStatusRef.current = currentStatus
  }, [telemetry?.status])

  const handleApproveModule = async () => {
    if (!sessionId) return
    setIsApproving(true)
    try {
      const res = await fetch('/api/session/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
      })
      if (!res.ok) {
        alert('Failed to approve module.')
      }
    } catch (err) {
      console.error(err)
    } finally {
      setIsApproving(false)
    }
  }

  const triggerPatchFetch = async (draftVal, instrVal, scopeVal) => {
    setIsQueryingPatch(true)
    setChatStatus('Querying AI Editor...')
    try {
      const res = await fetch('/api/session/edit/selection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          selection_text: draftVal,
          instruction: instrVal,
          theme: telemetry?.prompt_theme || 'default',
          full_text: content,
          scope: scopeVal
        })
      })
      if (res.ok) {
        const data = await res.json()
        setActivePatch(prev => ({
          ...prev,
          patchedText: data.patched_text
        }))
      } else {
        alert('Failed to generate patch suggestions.')
        setActivePatch(null)
      }
    } catch (err) {
      console.error(err)
      setActivePatch(null)
    } finally {
      setChatStatus('')
      setIsQueryingPatch(false)
    }
  }
 
  const handleAiSelectionPatch = () => {
    if (!selectedText || !aiInstruction || isQueryingPatch) return
    
    const original = selectedText
    const draftToUse = editScope === 'paragraph' ? _get_containing_paragraph(content, original) : original
    
    setActivePatch({
      originalText: draftToUse,
      patchedText: '',
      scope: editScope,
      instruction: aiInstruction
    })
    
    setShowAiModal(false)
    setAiInstruction('')
    clearActiveSelection()
    
    triggerPatchFetch(draftToUse, aiInstruction, editScope)
  }

  const handleRetryInlinePatch = () => {
    if (!activePatch || isQueryingPatch || !critiqueText.trim()) return
    const newInstruction = critiqueText.trim()
    
    setActivePatch(prev => ({
      ...prev,
      patchedText: '',
      instruction: `${prev.instruction} | Critique: ${newInstruction}`
    }))
    setCritiqueText('')
    
    triggerPatchFetch(activePatch.originalText, `${activePatch.instruction} | Critique: ${newInstruction}`, activePatch.scope)
  }

  const handleAcceptInlinePatch = () => {
    if (!activePatch) return
    const newContent = content.replace(activePatch.originalText, activePatch.patchedText)
    setContent(newContent)
    setActivePatch(null)
    
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

  const handleSendChatMessage = async () => {
    if (!chatPrompt.trim() || chatLoading) return
    const userMsg = { sender: 'user', text: chatPrompt }
    setChatMessages(prev => [...prev, userMsg])
    setChatPrompt('')
    setChatLoading(true)
    setChatStatus('Assistant is typing...')
    try {
      const res = await fetch('/api/session/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          submodule_filename: filename,
          message: userMsg.text
        })
      })
      if (res.ok) {
        const data = await res.json()
        setChatMessages(prev => [...prev, { sender: 'assistant', text: data.response }])
      } else {
        setChatMessages(prev => [...prev, { sender: 'assistant', text: 'Error: Failed to fetch assistant response.' }])
      }
    } catch (err) {
      setChatMessages(prev => [...prev, { sender: 'assistant', text: `Error: ${err.message}` }])
    } finally {
      setChatStatus('')
      setChatLoading(false)
    }
  }

  useEffect(() => {
    setContent(preview || '')
  }, [preview])

  // Dismiss floating popup on external click, but track container scrolls dynamically
  useEffect(() => {
    if (!selectionRange) return

    const handleDismiss = (e) => {
      if (popupRef.current && popupRef.current.contains(e.target)) return
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON' || e.target.closest('button') || e.target.closest('input')) return
      clearActiveSelection()
    }

    let scrollRafId = null
    const handleScroll = () => {
      if (scrollRafId) cancelAnimationFrame(scrollRafId)
      
      scrollRafId = requestAnimationFrame(() => {
        const container = containerRef.current
        if (!container) return

        const containerRect = container.getBoundingClientRect()
        
        // Calculate dynamic viewport coordinates using relative offsets and current scroll height
        const currentTop = selectionRelativeCoords.top - container.scrollTop + containerRect.top
        const currentLeft = selectionRelativeCoords.left - container.scrollLeft + containerRect.left

        // Hide popup if the selection scrolls out of the visible vertical container area
        const isOutOfViewport = 
          currentTop < containerRect.top || 
          currentTop > containerRect.bottom

        if (isOutOfViewport) {
          setIsPopupVisible(false)
        } else {
          setIsPopupVisible(true)
          const calculatedTop = currentTop - 58
          setSelectionCoords({
            top: Math.max(16, calculatedTop),
            left: currentLeft
          })
        }
      })
    }

    document.addEventListener('mousedown', handleDismiss)
    const container = containerRef.current
    if (container) container.addEventListener('scroll', handleScroll)

    return () => {
      document.removeEventListener('mousedown', handleDismiss)
      if (container) container.removeEventListener('scroll', handleScroll)
      if (scrollRafId) cancelAnimationFrame(scrollRafId)
    }
  }, [selectionRange, selectionRelativeCoords])

  // Resolve filename from session
  useEffect(() => {
    if (sessionId) {
      if (sessionId.startsWith('test_')) return
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
  const handleTextSelection = useCallback((e) => {
    // If clicking on an input or button, ignore selection handling completely
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON' || e.target.closest('button') || e.target.closest('input')) {
      return
    }

    // Lock selection if we are in the review/active-patch phase
    if (activeBatchPatches.some(p => p.status === 'pending')) {
      window.getSelection()?.removeAllRanges()
      return
    }

    // Don't dismiss if mouseup happened on the popup itself
    if (popupRef.current && popupRef.current.contains(e.target)) return

    const selection = window.getSelection()
    if (!selection || selection.isCollapsed) {
      // Only dismiss if click was NOT on popup (already handled above)
      setSelectionRange(null)
      return
    }
    const text = selection.toString().trim()
    if (text.length > 5) {
      const range = selection.getRangeAt(0)
      const rects = range.getClientRects()
      const firstRect = rects.length > 0 ? rects[0] : range.getBoundingClientRect()
      
      setSelectedText(text)
      setReplacementText(text)
      setSelectionRange(range)
      setIsPopupVisible(true)
      
      const container = containerRef.current
      const calculatedTop = firstRect.top - 58
      
      setSelectionCoords({
        top: Math.max(16, calculatedTop),
        left: firstRect.left + 15
      })

      if (container) {
        const containerRect = container.getBoundingClientRect()
        setSelectionRelativeCoords({
          top: firstRect.top - containerRect.top + container.scrollTop,
          left: firstRect.left - containerRect.left + container.scrollLeft + 15
        })
      }

      if (typeof Highlight !== 'undefined' && typeof CSS !== 'undefined' && CSS.highlights) {
        try {
          const highlight = new Highlight(range)
          CSS.highlights.set("user-selection", highlight)
        } catch (err) {
          console.warn("Failed to set CSS highlight:", err)
        }
      }
    }
  }, [activeBatchPatches])

  const applySelectionPatch = () => {
    if (!selectedText || !replacementText) return
    const newContent = content.replace(selectedText, replacementText)
    setContent(newContent)
    setShowHighlightModal(false)
    clearActiveSelection()
    
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

  const handleSelectMode = (mode) => {
    const matchInfo = findSelectionOffset(content, selectedText);
    if (matchInfo) {
      const snapped = mode === 'paragraph' 
        ? snapToParagraph(content, matchInfo) 
        : snapToSentences(content, matchInfo);
      if (snapped) {
        setSelectedText(snapped.text);
      }
    }
    setSelectedMode(mode);
  };

  const handleEnqueueComment = (instructionText) => {
    if (!selectedText || !instructionText.trim()) return
    saveScroll()
    const newEdit = {
      id: Math.random().toString(36).substring(2, 9),
      originalText: selectedText,
      instruction: instructionText
    }
    setQueuedEdits(prev => [...prev, newEdit])
    clearActiveSelection()
  }

  const handleContainerClick = (e) => {
    const removeBtn = e.target.closest('.remove-staged-btn')
    if (removeBtn) {
      e.preventDefault()
      e.stopPropagation()
      const editId = removeBtn.getAttribute('data-edit-id')
      if (editId) {
        saveScroll()
        setQueuedEdits(prev => prev.filter(item => item.id !== editId))
      }
    }
  }

  const handleProcessBatchEdits = async () => {
    if (queuedEdits.length === 0 || !sessionId) return
    setIsProcessingBatch(true)
    try {
      const res = await fetch('/api/session/edit/selection/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          theme: 'default',
          full_text: content,
          edits: queuedEdits.map(e => ({
            original_text: e.originalText,
            instruction: e.instruction
          }))
        })
      })
      if (res.ok) {
        const data = await res.json()
        const returnedPatches = data.patched_texts || []
        saveScroll()
        const mappedPatches = queuedEdits.map((e, idx) => ({
          ...e,
          patchedText: returnedPatches[idx] || '',
          status: 'pending'
        }))
        setActiveBatchPatches(mappedPatches)
        setQueuedEdits([]) // Clear queue as edits are processed
      } else {
        alert('Failed to process batch edits.')
      }
    } catch (err) {
      console.error(err)
    } finally {
      setIsProcessingBatch(false)
    }
  }

  const handleAcceptBatchPatch = (id, patchedText) => {
    const patch = activeBatchPatches.find(p => p.id === id)
    if (!patch) return
    
    saveScroll()
    // Merge patch text into local draft
    const newContent = content.replace(patch.originalText, patchedText)
    setContent(newContent)
    
    // Update patch status
    setActiveBatchPatches(prev => {
      const nextPatches = prev.map(p => p.id === id ? { ...p, status: 'accepted' } : p);
      if (!nextPatches.some(p => p.status === 'pending')) {
        return [];
      }
      return nextPatches;
    });

    // Automatically save updated text to backend
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

  const handleRejectBatchPatch = (id) => {
    saveScroll()
    setActiveBatchPatches(prev => {
      const nextPatches = prev.map(p => p.id === id ? { ...p, status: 'rejected' } : p);
      if (!nextPatches.some(p => p.status === 'pending')) {
        return [];
      }
      return nextPatches;
    });
  }

  const handleRetryBatchPatch = async (id, originalText, newInstruction) => {
    // Isolated single patch regenerate
    saveScroll()
    setActiveBatchPatches(prev => prev.map(p => p.id === id ? { ...p, status: 'pending', patchedText: '', instruction: newInstruction } : p))
    try {
      const res = await fetch('/api/session/edit/selection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          selection_text: originalText,
          instruction: newInstruction,
          theme: 'default',
          full_text: content,
          scope: 'selection'
        })
      })
      if (res.ok) {
        const data = await res.json()
        setActiveBatchPatches(prev => prev.map(p => p.id === id ? { ...p, patchedText: data.patched_text } : p))
      } else {
        alert('Failed to regenerate section.')
      }
    } catch (err) {
      console.error(err)
    }
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

  const renderContentWithDiff = () => {
    if (!activePatch) return null;
    const idx = content.indexOf(activePatch.originalText);
    if (idx === -1) {
      return (
        <div className="w-full select-text">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
            {content}
          </ReactMarkdown>
        </div>
      );
    }
    
    const before = content.slice(0, idx);
    const after = content.slice(idx + activePatch.originalText.length);
    
    return (
      <div className="w-full select-text flex flex-col gap-4">
        {before.trim() && (
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
            {before}
          </ReactMarkdown>
        )}
        
        {/* Inline Suggestion Block - Integrated into the Main Render Flow */}
        <div className="my-3 border-l-4 border-amber-500/70 pl-4 py-2 bg-zinc-900/10 rounded-r-xl">
          <div className="text-[10px] uppercase font-bold text-amber-500/80 mb-2 tracking-wider select-none">
            Proposed Inline Diff
          </div>
          
          <div className="text-sm leading-relaxed mb-4 flex flex-col gap-3">
            {/* Red Strikethrough for Deleted text */}
            <div className="text-red-400 bg-red-950/20 line-through px-2.5 py-1.5 rounded-lg border border-red-900/10 select-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {activePatch.originalText}
              </ReactMarkdown>
            </div>
            
            {/* Green text for Inserted text */}
            {!activePatch.patchedText ? (
              <span className="inline-flex items-center gap-1.5 text-zinc-500 italic text-xs animate-pulse">
                <span className="w-3 h-3 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
                Generating patch...
              </span>
            ) : (
              <div className="text-emerald-400 bg-emerald-950/20 px-2.5 py-1.5 rounded-lg border border-emerald-900/10">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                  {activePatch.patchedText}
                </ReactMarkdown>
              </div>
            )}
          </div>
          
          {/* Action Toolbar & Feedback Input */}
          <div className="flex flex-col gap-2.5 max-w-xl bg-zinc-950/40 p-3 rounded-lg border border-zinc-900">
            <div className="flex gap-2">
              <button
                onClick={handleAcceptInlinePatch}
                disabled={!activePatch.patchedText || isQueryingPatch}
                className="bg-emerald-500 hover:bg-emerald-600 disabled:opacity-40 text-zinc-950 font-bold px-3 py-1.5 rounded-md text-xs transition-all flex items-center gap-1 active:scale-95 duration-75"
              >
                <CheckCircle className="w-3.5 h-3.5" />
                Accept & Merge
              </button>
              <button
                onClick={() => setActivePatch(null)}
                className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-3 py-1.5 rounded-md text-xs border border-zinc-700 transition-all flex items-center gap-1 active:scale-95 duration-75"
              >
                <X className="w-3.5 h-3.5" />
                Reject
              </button>
            </div>
            
            {activePatch.patchedText && (
              <div className="flex gap-2 pt-2 border-t border-zinc-900">
                <input
                  type="text"
                  value={critiqueText}
                  onChange={(e) => setCritiqueText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleRetryInlinePatch()
                  }}
                  disabled={isQueryingPatch}
                  placeholder="Tell AI what is right/wrong about this..."
                  className="flex-1 px-3 py-1.5 text-xs bg-zinc-900 border border-zinc-800 rounded-md text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-zinc-700 font-sans disabled:opacity-50 select-text"
                />
                <button
                  onClick={handleRetryInlinePatch}
                  disabled={isQueryingPatch || !critiqueText.trim()}
                  className="bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-zinc-950 font-bold px-3 rounded-md text-xs transition-all active:scale-95 duration-75"
                >
                  {isQueryingPatch ? 'Regenerating...' : 'Retry'}
                </button>
              </div>
            )}
          </div>
        </div>
        
        {after.trim() && (
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
            {after}
          </ReactMarkdown>
        )}
      </div>
    );
  };

  const findSelectionOffset = (fullText, selectionText) => {
    if (!selectionText) return null;
    
    const words = selectionText.split(/\s+/).filter(Boolean);
    if (words.length === 0) return null;
    
    // 1. Try fuzzy regex match of the entire block
    const escapedWords = words.map(w => w.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&'));
    const fuzzyPattern = escapedWords.join('[\\s\\*#_\\-\\>\\[\\]\\(\\)]+');
    try {
      const match = fullText.match(new RegExp(fuzzyPattern, 'i'));
      if (match) {
        return { index: match.index, length: match[0].length };
      }
    } catch (e) {}

    // 2. Try phrase matching (using first 3 words to find unique index)
    const firstPhrase = words.slice(0, Math.min(3, words.length)).join(' ');
    const escapedPhrase = firstPhrase.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&').replace(/\s+/g, '[\\s\\*#_\\-\\>\\[\\]\\(\\)]+');
    
    let idx = -1;
    try {
      const match = fullText.match(new RegExp(escapedPhrase, 'i'));
      if (match) idx = match.index;
    } catch (e) {}
    
    if (idx === -1) {
      idx = fullText.indexOf(words[0]);
    }
    
    if (idx !== -1) {
      // Find the last phrase
      const lastPhrase = words.slice(-Math.min(3, words.length)).join(' ');
      const escapedLast = lastPhrase.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&').replace(/\s+/g, '[\\s\\*#_\\-\\>\\[\\]\\(\\)]+');
      let lastIdx = -1;
      try {
        const match = fullText.slice(idx).match(new RegExp(escapedLast, 'i'));
        if (match) lastIdx = idx + match.index;
      } catch (e) {}
      
      if (lastIdx === -1) {
        lastIdx = fullText.indexOf(words[words.length - 1], idx + words[0].length);
      }
      
      const length = lastIdx !== -1 
        ? (lastIdx + (words.slice(-Math.min(3, words.length)).join(' ').length) - idx)
        : selectionText.length;
        
      return { index: idx, length: length };
    }
    return null;
  };

  const snapToSentences = (fullText, matchInfo) => {
    if (!matchInfo) return null;
    const preceding = fullText.slice(0, matchInfo.index);
    const lastTerminator = Math.max(
      preceding.lastIndexOf('. '),
      preceding.lastIndexOf('? '),
      preceding.lastIndexOf('! '),
      preceding.lastIndexOf('\n')
    );
    let snapStart = 0;
    if (lastTerminator !== -1) {
      snapStart = lastTerminator + (preceding[lastTerminator] === '\n' ? 1 : 2);
    }

    const following = fullText.slice(matchInfo.index + matchInfo.length);
    const matchTerminator = following.match(/[\.\?\!\n]/);
    let snapEnd = fullText.length;
    if (matchTerminator) {
      const termIndex = matchTerminator.index;
      const termChar = matchTerminator[0];
      snapEnd = matchInfo.index + matchInfo.length + termIndex + (termChar === '\n' ? 0 : 1);
    }
    return {
      text: fullText.slice(snapStart, snapEnd),
      index: snapStart,
      length: snapEnd - snapStart
    };
  };

  const snapToParagraph = (fullText, matchInfo) => {
    const ctx = getParagraphContext(fullText, matchInfo);
    if (!ctx) return null;
    const start = matchInfo.index - ctx.before.length;
    const length = ctx.before.length + matchInfo.length + ctx.after.length;
    return {
      text: fullText.slice(start, start + length),
      index: start,
      length: length
    };
  };

  const getParagraphContext = (fullText, matchInfo) => {
    if (!matchInfo) return null;
    
    const precedingText = fullText.slice(0, matchInfo.index);
    const lastDoubleNewline = precedingText.lastIndexOf('\n\n');
    
    // Check if there is a heading in the preceding block
    let lastHeading = -1;
    try {
      // Find the last markdown heading start index in preceding text
      const headingMatches = [...precedingText.matchAll(/\n#+\s+/g)];
      if (headingMatches.length > 0) {
        lastHeading = headingMatches[headingMatches.length - 1].index;
      } else if (precedingText.startsWith('#')) {
        lastHeading = 0;
      }
    } catch (e) {}

    // Check if there is a list item start in preceding text
    let lastBullet = -1;
    try {
      const bulletMatches = [...precedingText.matchAll(/\n\s*([-*]|\d+\.)\s+/g)];
      if (bulletMatches.length > 0) {
        lastBullet = bulletMatches[bulletMatches.length - 1].index;
      }
    } catch (e) {}

    let paraStart = 0;
    if (lastDoubleNewline !== -1) paraStart = lastDoubleNewline + 2;
    if (lastHeading !== -1 && lastHeading > lastDoubleNewline) {
      paraStart = lastHeading;
    }
    // If a bullet point is closer than the double newline/heading, snap to the bullet start
    if (lastBullet !== -1 && lastBullet > paraStart) {
      paraStart = lastBullet + 1; // +1 to skip the leading newline
    }

    const followingText = fullText.slice(matchInfo.index + matchInfo.length);
    const nextDoubleNewline = followingText.indexOf('\n\n');
    
    let nextHeading = -1;
    try {
      const headingMatch = followingText.match(/\n#+\s+/);
      if (headingMatch) {
        nextHeading = headingMatch.index;
      }
    } catch (e) {}

    let nextBullet = -1;
    try {
      const bulletMatch = followingText.match(/\n\s*([-*]|\d+\.)\s+/);
      if (bulletMatch) {
        nextBullet = bulletMatch.index;
      }
    } catch (e) {}

    let paraEnd = fullText.length;
    const candidates = [];
    if (nextDoubleNewline !== -1) candidates.push(matchInfo.index + matchInfo.length + nextDoubleNewline);
    if (nextHeading !== -1) candidates.push(matchInfo.index + matchInfo.length + nextHeading);
    if (nextBullet !== -1) candidates.push(matchInfo.index + matchInfo.length + nextBullet);
    
    if (candidates.length > 0) {
      paraEnd = Math.min(...candidates);
    }

    return {
      before: fullText.slice(paraStart, matchInfo.index),
      selection: fullText.slice(matchInfo.index, matchInfo.index + matchInfo.length),
      after: fullText.slice(matchInfo.index + matchInfo.length, paraEnd)
    };
  };

  const wrapMultiParagraphHtml = (text, className) => {
    if (!text) return '';
    if (!className) return text;
    // Strip leading markdown heading tokens from each line before injecting into HTML spans.
    // Inside an HTML <span>, remark-gfm can no longer parse "#### Heading" as a heading —
    // it renders the raw '#' characters as literal text. Stripping them makes the content
    // render cleanly as normal paragraph text within the diff highlight.
    const stripHeadings = (str) =>
      str.split('\n').map(line => line.replace(/^#{1,6}\s+/, '')).join('\n');
      
    // Split by double newline or single newline followed by a list marker, keeping separators at odd indices
    const tokens = text.split(/(\n\n|\n(?=\s*(?:[-*]|\d+\.)\s+))/);
    return tokens.map((token, idx) => {
      if (idx % 2 === 1) return token; // Keep separators unchanged
      if (!token.trim()) return token;
      
      const cleanToken = stripHeadings(token);
      
      // Match markdown list markers at the start of the token
      const listMatch = cleanToken.match(/^(\s*(?:[-*]|\d+\.)\s+)([\s\S]*)$/);
      if (listMatch) {
        const [, marker, rest] = listMatch;
        return `${marker}<span class="${className}">${rest}</span>`;
      }
      
      return `<span class="${className}">${cleanToken}</span>`;
    }).join('');
  };

  const reconstructParagraphHtml = (before, matchText, after, className) => {
    const wrappedMatch = wrapMultiParagraphHtml(matchText, className);
    return `${before}${wrappedMatch}${after}`;
  };

  const renderContentWithStagedHighlights = () => {
    if (queuedEdits.length === 0) {
      return (
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
          {content}
        </ReactMarkdown>
      );
    }

    const sortedEdits = [...queuedEdits]
      .map(edit => {
        const matchInfo = findSelectionOffset(content, edit.originalText);
        return matchInfo ? { ...edit, index: matchInfo.index, length: matchInfo.length } : null;
      })
      .filter(Boolean)
      .sort((a, b) => a.index - b.index);

    if (sortedEdits.length === 0) {
      return (
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
          {content}
        </ReactMarkdown>
      );
    }

    const elements = [];
    let currentIdx = 0;

    sortedEdits.forEach((edit) => {
      const ctx = getParagraphContext(content, edit);
      if (!ctx) return;

      const ctxStart = edit.index - ctx.before.length;
      const ctxEnd = edit.index + edit.length + ctx.after.length;

      // 1. Render Markdown segment before the paragraph context
      if (ctxStart > currentIdx) {
        const beforeText = content.slice(currentIdx, ctxStart);
        elements.push(
          <ReactMarkdown key={`before-${edit.id}`} remarkPlugins={[remarkGfm]} components={markdownComponents}>
            {beforeText}
          </ReactMarkdown>
        );
      }

      // Prepare paragraph with inline highlighted selection range
      const paragraphHtml = reconstructParagraphHtml(ctx.before, ctx.selection, ctx.after, 'staged-inner-highlight');

      // 2. Render Staged Card containing the full context paragraph
      elements.push(
        <div key={`staged-${edit.id}`} className="my-4 border-l-4 border-amber-500/50 pl-4 py-2.5 bg-zinc-900/10 rounded-r-xl w-full">
          <div className="text-[10px] uppercase font-bold text-amber-500/80 mb-1.5 tracking-wider flex items-center justify-between select-none">
            <span className="flex items-center gap-1.5">
              <Sparkles className="w-3 h-3 text-amber-500" />
              Staged Edit Feedback
            </span>
            <button
              onClick={() => setQueuedEdits(prev => prev.filter(item => item.id !== edit.id))}
              className="text-[9px] bg-zinc-800/80 hover:bg-red-950/40 hover:text-red-400 border border-zinc-750 px-2 py-0.5 rounded transition-all"
            >
              Cancel
            </button>
          </div>
          <div className="text-xs text-zinc-400 italic mb-2">
            Requested: "{edit.instruction}"
          </div>
          <div className="text-sm leading-relaxed text-zinc-300 select-text">
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} components={markdownComponents}>
              {paragraphHtml}
            </ReactMarkdown>
          </div>
        </div>
      );

      currentIdx = ctxEnd;
    });

    if (currentIdx < content.length) {
      const trailingText = content.slice(currentIdx);
      elements.push(
        <ReactMarkdown key="trailing" remarkPlugins={[remarkGfm]} components={markdownComponents}>
          {trailingText}
        </ReactMarkdown>
      );
    }

    return <div className="w-full flex flex-col gap-4">{elements}</div>;
  };

  const renderContentWithBatchDiffs = () => {
    // Filter active patches to show only those not currently accepted (accepted patches are already merged in draft content)
    const pendingPatches = activeBatchPatches.filter(p => p.status === 'pending');
    
    if (pendingPatches.length === 0) {
      return (
        <div className="w-full select-text">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
            {content}
          </ReactMarkdown>
        </div>
      );
    }

    // Sort pending patches by their appearance in the text
    const sortedPatches = [...pendingPatches]
      .map(p => {
        const matchInfo = findSelectionOffset(content, p.originalText);
        return matchInfo ? { ...p, index: matchInfo.index, length: matchInfo.length } : null;
      })
      .filter(Boolean)
      .sort((a, b) => a.index - b.index);

    if (sortedPatches.length === 0) {
      return (
        <div className="w-full select-text">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
            {content}
          </ReactMarkdown>
        </div>
      );
    }

    const elements = [];
    let currentIdx = 0;

    sortedPatches.forEach((patch, idx) => {
      const ctx = getParagraphContext(content, patch);
      if (!ctx) return;

      const ctxStart = patch.index - ctx.before.length;
      const ctxEnd = patch.index + patch.length + ctx.after.length;

      // 1. Render Markdown segment before the patch context
      if (ctxStart > currentIdx) {
        const beforeText = content.slice(currentIdx, ctxStart);
        elements.push(
          <ReactMarkdown key={`before-${patch.id}`} remarkPlugins={[remarkGfm]} components={markdownComponents}>
            {beforeText}
          </ReactMarkdown>
        );
      }

      // Prepare context paragraphs with inline diff tags
      const deletedParagraphHtml = reconstructParagraphHtml(ctx.before, ctx.selection, ctx.after, 'diff-deleted');
      const insertedParagraphHtml = reconstructParagraphHtml(ctx.before, patch.patchedText || '', ctx.after, 'diff-inserted');

      // 2. Render Interactive Inline Diff Block (showing the surrounding paragraph context)
      elements.push(
        <div key={`diff-${patch.id}`} className="my-4 border-l-4 border-amber-500/70 pl-4 py-2 bg-zinc-900/10 rounded-r-xl w-full">
          <div className="text-[10px] uppercase font-bold text-amber-500/80 mb-2 tracking-wider flex items-center gap-1.5 select-none">
            <Sparkles className="w-3 h-3 text-amber-500" />
            Proposed Change
          </div>
          
          <div className="text-sm leading-relaxed mb-4 flex flex-col gap-3">
            {/* Red Strikethrough for Deleted text */}
            <div className="text-zinc-300 bg-zinc-950/20 px-2.5 py-1.5 rounded-lg border border-red-900/10 select-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} components={markdownComponents}>
                {deletedParagraphHtml}
              </ReactMarkdown>
            </div>
            
            {/* Green text for Inserted text */}
            {!patch.patchedText ? (
              <span className="inline-flex items-center gap-1.5 text-zinc-500 italic text-xs animate-pulse">
                <span className="w-3 h-3 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
                Generating patch...
              </span>
            ) : (
              <div className="text-zinc-200 bg-zinc-950/20 px-2.5 py-1.5 rounded-lg border border-emerald-900/10 select-text">
                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} components={markdownComponents}>
                  {insertedParagraphHtml}
                </ReactMarkdown>
              </div>
            )}
          </div>
          
          {/* Action Toolbar & Feedback Input */}
          <div className="flex flex-col gap-2.5 max-w-xl bg-zinc-950/40 p-3 rounded-lg border border-zinc-900">
            <div className="flex gap-2">
              <button
                onClick={() => handleAcceptBatchPatch(patch.id, patch.patchedText)}
                disabled={!patch.patchedText}
                className="bg-emerald-500 hover:bg-emerald-600 disabled:opacity-40 text-zinc-955 font-bold px-3 py-1.5 rounded-md text-xs transition-all flex items-center gap-1 active:scale-95 duration-75"
              >
                <Check className="w-3.5 h-3.5" />
                Accept & Merge
              </button>
              <button
                onClick={() => handleRejectBatchPatch(patch.id)}
                className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-3 py-1.5 rounded-md text-xs border border-zinc-700 transition-all flex items-center gap-1 active:scale-95 duration-75"
              >
                <X className="w-3.5 h-3.5" />
                Reject
              </button>
            </div>
            
            {patch.patchedText && (
              <div className="flex gap-2 pt-2 border-t border-zinc-900">
                <input
                  type="text"
                  placeholder="Request changes specifically to this section..."
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && e.target.value.trim()) {
                      handleRetryBatchPatch(patch.id, patch.originalText, e.target.value)
                      e.target.value = ''
                    }
                  }}
                  className="flex-1 px-3 py-1.5 text-xs bg-zinc-900 border border-zinc-800 rounded-md text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-zinc-700 font-sans select-text"
                />
                <button
                  onClick={(e) => {
                    const input = e.currentTarget.previousSibling
                    if (input && input.value.trim()) {
                      handleRetryBatchPatch(patch.id, patch.originalText, input.value)
                      input.value = ''
                    }
                  }}
                  className="bg-amber-500 hover:bg-amber-600 text-zinc-950 font-bold px-3 rounded-md text-xs transition-all active:scale-95 duration-75"
                >
                  Retry
                </button>
              </div>
            )}
          </div>
        </div>
      );

      currentIdx = ctxEnd;
    });

    // 3. Render any trailing markdown content
    if (currentIdx < content.length) {
      const trailingText = content.slice(currentIdx);
      elements.push(
        <ReactMarkdown key="trailing" remarkPlugins={[remarkGfm]} components={markdownComponents}>
          {trailingText}
        </ReactMarkdown>
      );
    }

    return <div className="w-full select-text flex flex-col gap-4">{elements}</div>;
  };

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

  if (isActive || !lastRenderedContent.current) {
    lastRenderedContent.current = (
      <div className={editMode ? 'hidden' : 'w-full flex flex-col'}>
        {activeBatchPatches.length > 0 ? (
          renderContentWithBatchDiffs()
        ) : activePatch ? (
          renderContentWithDiff()
        ) : (
          renderContentWithStagedHighlights()
        )}
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

          {isReviewing && (
            <Badge variant="outline" className="ml-2 bg-amber-500/10 text-amber-400 border-amber-500/20 text-[10px] tracking-widest px-2.5 py-0 h-5 rounded-full flex items-center gap-1 animate-pulse">
              <AlertTriangle className="w-3 h-3" />
              PAUSED FOR REVIEW
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

            {(isPaused || isReviewing) && (
              <button
                onClick={() => setShowChat(!showChat)}
                className={`text-xs px-3 py-1.5 rounded-lg border transition-colors flex items-center gap-1.5 ${showChat ? 'bg-amber-500/20 text-amber-300 border-amber-500/30' : 'bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border-zinc-800/80'}`}
              >
                <MessageSquare className="w-3.5 h-3.5" />
                {isPaused ? 'Repair Chat' : 'Review Chat'}
              </button>
            )}

            {isReviewing && (
              <button
                onClick={handleApproveModule}
                disabled={isApproving}
                className="text-xs bg-gradient-to-r from-amber-500 to-amber-600 hover:from-emerald-500 hover:to-emerald-600 text-zinc-950 font-bold px-4 py-1.5 rounded-lg transition-all duration-300 flex items-center gap-1.5 shadow-[0_0_10px_rgba(245,158,11,0.15)] active:scale-95 disabled:opacity-50"
              >
                <CheckCircle className="w-3.5 h-3.5" />
                {isApproving ? 'Approving...' : 'Approve & Continue'}
              </button>
            )}
          </div>
        </div>

        {showCompletionBadge && (
          <div className="absolute top-16 left-1/2 transform -translate-x-1/2 z-30 animate-bounce">
            <button
              onClick={() => {
                containerRef.current?.scrollTo({ top: 0, behavior: 'smooth' })
                setShowCompletionBadge(false)
              }}
              className="bg-amber-500 hover:bg-amber-600 active:scale-95 text-zinc-950 font-bold px-4 py-2 rounded-full text-xs shadow-[0_4px_20px_rgba(245,158,11,0.4)] flex items-center gap-1.5 transition-all"
            >
              <span>✨ Textbook complete! Go to top</span>
            </button>
          </div>
        )}

        {/* Text Area or Markdown view */}
        <div 
          className={`flex-1 preview-content overflow-auto py-12 px-4 md:px-8 lg:px-12 scroll-smooth min-h-0 min-w-0 custom-scrollbar flex flex-col items-center relative ${activeBatchPatches.some(p => p.status === 'pending' && !p.patchedText) ? 'select-none' : ''}`} 
          ref={containerRef} 
          onMouseUp={editMode ? null : handleTextSelection} 
          onClick={editMode ? null : handleContainerClick}
        >
          <div className="w-full max-w-3xl flex-1 flex flex-col">
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className={`flex-1 w-full min-h-[500px] p-6 text-sm font-mono bg-zinc-900/50 border border-zinc-850 rounded-2xl text-zinc-200 focus:outline-none focus:border-zinc-700 focus:ring-1 focus:ring-zinc-700 transition-all custom-scrollbar whitespace-pre-wrap leading-relaxed resize-none ${!editMode ? 'hidden' : ''}`}
            />
            {lastRenderedContent.current}
          </div>

        </div>

        {/* Floating Highlight Patcher Popup — fixed to viewport, outside overflow container */}
        {selectionRange && isPopupVisible && (
          <div
            ref={popupRef}
            style={{
              position: 'fixed',
              top: `${selectionCoords.top}px`,
              left: `${selectionCoords.left}px`,
              transform: 'translateX(-50%)',
              zIndex: 9999
            }}
            className="bg-zinc-950/98 border border-zinc-800/80 rounded-xl p-2.5 flex items-center gap-2.5 shadow-[0_12px_40px_rgba(0,0,0,0.85)] animate-in fade-in zoom-in-95 duration-100 min-w-[320px]"
            onMouseDown={(e) => e.stopPropagation()}
          >
            {!selectedMode ? (
              <>
                <span className="text-[10px] uppercase font-bold text-zinc-500 select-none mr-1 tracking-wider">Snap to:</span>
                <button
                  onClick={() => handleSelectMode('sentence')}
                  className="text-xs bg-zinc-900 hover:bg-zinc-850 hover:text-amber-400 text-zinc-300 px-3 py-1.5 rounded-lg border border-zinc-800 transition-all font-sans active:scale-95 duration-75 flex items-center gap-1 font-semibold"
                >
                  Selected Sentences
                </button>
                <button
                  onClick={() => handleSelectMode('paragraph')}
                  className="text-xs bg-zinc-900 hover:bg-zinc-850 hover:text-amber-400 text-zinc-300 px-3 py-1.5 rounded-lg border border-zinc-800 transition-all font-sans active:scale-95 duration-75 flex items-center gap-1 font-semibold"
                >
                  Entire Paragraph
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => setSelectedMode(null)}
                  className="p-1 text-zinc-500 hover:text-zinc-350 hover:bg-zinc-900 rounded-lg transition-colors shrink-0"
                  title="Change Selection Range Mode"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                </button>
                <input
                  type="text"
                  placeholder={`Type instructions to edit ${selectedMode === 'paragraph' ? 'this paragraph' : 'these sentences'}...`}
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleEnqueueComment(e.target.value)
                      e.target.value = ''
                    }
                  }}
                  className="flex-1 bg-zinc-950 border border-zinc-850 rounded-lg px-2.5 py-1 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-zinc-700 font-sans"
                />
                <button
                  onClick={(e) => {
                    const input = e.currentTarget.previousSibling
                    if (input && input.value) {
                      handleEnqueueComment(input.value)
                      input.value = ''
                    }
                  }}
                  className="text-[10px] font-bold bg-amber-500 hover:bg-amber-600 text-zinc-950 px-2.5 py-1 rounded-lg transition-colors shrink-0"
                >
                  Add
                </button>
              </>
            )}
            <div className="w-px h-5 bg-zinc-800 shrink-0 self-center" />
             <button
              onClick={() => {
                clearActiveSelection()
              }}
              className="p-1 text-zinc-500 hover:text-zinc-300 rounded-lg hover:bg-zinc-900 transition-colors shrink-0"
            >
              <X className="w-3.5 h-3.5" />
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
                  Apply Edits
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

        {/* AI Selection Instruction Modal */}
        {showAiModal && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-md w-full p-6 flex flex-col gap-4 shadow-2xl animate-in zoom-in-95 duration-150">
              <div className="flex justify-between items-center">
                <h3 className="font-semibold text-zinc-200 text-sm">AI Selection Repair</h3>
                <button onClick={() => setShowAiModal(false)} className="text-zinc-500 hover:text-zinc-300"><X className="w-4 h-4" /></button>
              </div>
              <div className="flex flex-col gap-1.5">
                <span className="text-[10px] text-zinc-400 uppercase tracking-wide">Edit Scope</span>
                <div className="flex gap-1 bg-zinc-950 p-1 rounded-xl border border-zinc-800">
                  <button
                    onClick={() => setEditScope('selection')}
                    className={`flex-1 text-[11px] py-1.5 rounded-lg transition-colors font-sans ${editScope === 'selection' ? 'bg-zinc-800 text-amber-400 font-bold' : 'text-zinc-400 hover:text-zinc-300'}`}
                  >
                    Selection Only
                  </button>
                  <button
                    onClick={() => setEditScope('paragraph')}
                    className={`flex-1 text-[11px] py-1.5 rounded-lg transition-colors font-sans ${editScope === 'paragraph' ? 'bg-zinc-800 text-amber-400 font-bold' : 'text-zinc-400 hover:text-zinc-300'}`}
                  >
                    Containing Paragraph
                  </button>
                </div>
              </div>
              <p className="text-[10px] text-zinc-400 mt-1">Instruct the agent how you want this block updated:</p>
              <textarea
                placeholder="e.g. explain this concept with an analogy"
                value={aiInstruction}
                onChange={(e) => setAiInstruction(e.target.value)}
                className="w-full h-20 p-3 text-xs bg-zinc-950 border border-zinc-800 focus:border-zinc-700 rounded-xl text-zinc-300 resize-none focus:outline-none font-sans transition-all"
              />
              <div className="flex justify-end gap-2.5 text-xs pt-1.5 pb-2">
                <button
                  onClick={handleAiSelectionPatch}
                  disabled={isQueryingPatch}
                  className="bg-amber-500 hover:bg-amber-600 text-zinc-950 font-bold px-4 py-2.5 rounded-xl transition-all flex items-center gap-1.5 active:scale-95 disabled:opacity-50"
                >
                  {isQueryingPatch ? (
                    <>
                      <span className="w-3.5 h-3.5 border-2 border-zinc-950 border-t-transparent rounded-full animate-spin" />
                      Generating Patch...
                    </>
                  ) : (
                    'Suggest Inline Repair'
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
        {/* Diff Comparison Viewer Modal */}

      </div>

      {/* Collapsible Sidebar Chat Panel for Breakpoint/Validation Recovery & Review Conversational Chat */}
      {showChat && (isPaused || isReviewing) && (
        <div className="w-80 shrink-0 border-l border-zinc-850 bg-zinc-900/40 backdrop-blur-xl flex flex-col h-full z-20">
          <div className="flex-shrink-0 flex items-center justify-between px-6 py-4 border-b border-zinc-850 bg-zinc-900/80">
            <span className="text-xs font-bold text-zinc-300 tracking-wide uppercase flex items-center gap-1.5">
              <MessageSquare className="w-4 h-4 text-amber-400" />
              {isPaused ? 'Repair Assistant' : 'Review Assistant'}
            </span>
            <button onClick={() => setShowChat(false)} className="text-zinc-500 hover:text-zinc-300">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 overflow-auto p-4 flex flex-col gap-4 custom-scrollbar">
            {isPaused ? (
              <>
                {/* Blocker details (only in repair mode) */}
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
                    className="w-full h-24 p-3 text-xs bg-zinc-950 border border-zinc-850 rounded-xl text-zinc-300 placeholder-zinc-600 focus:outline-none focus:border-zinc-700 resize-none font-sans"
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
              </>
            ) : (
              <>
                {/* Conversational review chat logs */}
                <div className="flex-1 flex flex-col gap-3 min-h-0 min-w-0 overflow-auto pb-4">
                  {chatMessages.length === 0 && (
                    <div className="text-xs text-zinc-500 italic text-center mt-8 px-4 leading-relaxed">
                      Converse with the Review Assistant to rewrite, format, or adjust draft text blocks.
                    </div>
                  )}
                  {chatMessages.map((msg, idx) => {
                    const isUser = msg.sender === 'user'
                    return (
                      <div key={idx} className={`flex flex-col max-w-[90%] ${isUser ? 'self-end items-end' : 'self-start items-start'}`}>
                        <div className={`p-3 rounded-2xl text-xs leading-relaxed ${isUser ? 'bg-amber-500/10 text-amber-200 border border-amber-500/20 rounded-tr-none' : 'bg-zinc-900 text-zinc-300 border border-zinc-800 rounded-tl-none'}`}>
                          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                            {msg.text}
                          </ReactMarkdown>
                        </div>
                        {/* Interactive Revision Applier shortcut */}
                        {!isUser && msg.text.includes('```') && (
                          <button
                            onClick={() => {
                              const match = msg.text.match(/```(?:markdown)?([\s\S]*?)```/)
                              if (match && match[1]) {
                                setContent(match[1].trim())
                              }
                            }}
                            className="mt-1.5 text-[9px] bg-zinc-800 hover:bg-zinc-750 text-zinc-300 px-2 py-1 rounded-lg border border-zinc-700/50 flex items-center gap-1 transition-colors self-start shadow-sm active:scale-95"
                          >
                            <CheckCircle className="w-3 h-3 text-emerald-400" />
                            Apply Revision to Editor
                          </button>
                        )}
                      </div>
                    )
                  })}
                  {chatLoading && (
                    <div className="flex items-center gap-1 bg-zinc-900 border border-zinc-800 text-zinc-400 p-2.5 rounded-2xl rounded-tl-none self-start max-w-[60%] select-none">
                      <div className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  )}
                </div>

                {/* Message send controls */}
                <div className="flex-shrink-0 flex gap-2 pt-2 border-t border-zinc-850">
                  <input
                    type="text"
                    value={chatPrompt}
                    onChange={(e) => setChatPrompt(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSendChatMessage()
                    }}
                    disabled={chatLoading}
                    placeholder={chatLoading ? 'Assistant is typing...' : 'Type feedback...'}
                    className="flex-1 p-2.5 text-xs bg-zinc-950 border border-zinc-850 rounded-xl text-zinc-300 placeholder-zinc-650 focus:outline-none focus:border-zinc-700 font-sans disabled:opacity-50"
                  />
                  <button
                    onClick={handleSendChatMessage}
                    disabled={chatLoading || !chatPrompt.trim()}
                    className="bg-amber-500 hover:bg-amber-600 text-zinc-950 font-bold px-3.5 rounded-xl text-xs transition-all shadow-md active:scale-95 disabled:opacity-50"
                  >
                    Send
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
      {/* Batch Processing Dock */}
      {queuedEdits.length > 0 && (
        <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 bg-zinc-950/80 backdrop-blur-md border border-zinc-800/80 rounded-2xl px-5 py-3.5 flex items-center gap-6 shadow-[0_20px_50px_rgba(0,0,0,0.5)] z-[9998] animate-in slide-in-from-bottom-4 duration-300">
          <div className="flex items-center gap-2">
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
            </span>
            <span className="text-xs font-medium text-zinc-300 font-sans">
              {queuedEdits.length} {queuedEdits.length === 1 ? 'edit' : 'edits'} queued
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleProcessBatchEdits}
              disabled={isProcessingBatch}
              className="text-xs font-bold bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 disabled:opacity-40 text-zinc-950 px-4 py-2 rounded-xl transition-all shadow-md active:scale-95 duration-100 flex items-center gap-1.5"
            >
              {isProcessingBatch ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-zinc-950 border-t-transparent rounded-full animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  Process Edits
                </>
              )}
            </button>
            <button
              onClick={() => {
                saveScroll()
                setQueuedEdits([])
              }}
              disabled={isProcessingBatch}
              className="text-xs font-medium text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900 border border-zinc-800/60 px-3.5 py-2 rounded-xl transition-colors"
            >
              Clear Queue
            </button>
          </div>
        </div>
      )}
    </div>
  )
})
