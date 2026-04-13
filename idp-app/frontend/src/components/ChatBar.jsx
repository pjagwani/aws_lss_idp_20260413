import { useState, useRef, useEffect } from 'react'
import { Send, Sparkles, Loader2, Copy, Check } from 'lucide-react'

const PROMPTS = [
  { label: 'Extract All Fields', prompt: 'Extract all handwritten fields from this document and return the results as structured JSON, including product name, batch number, ingredient names, weights, lot numbers, equipment IDs, operator initials, and timestamps.' },
  { label: 'Ingredients Only', prompt: 'Extract only the ingredient names and their corresponding weights in kg. Return the results as a JSON array of objects with "ingredient_name" and "weight_kg" fields.' },
  { label: 'Validate Batch #', prompt: 'Extract the batch number and operator initials. The expected batch number is "BMR-2024-0847" and the expected operator initials are "JKL". Compare your extracted values against these expected values and report whether each field matches.' },
  { label: 'Compliance Summary', prompt: 'Provide a compliance summary for this batch record. Identify any ALCOA+ violations, missing required fields, and recommend corrective actions.' },
]

function CopyBtn({ text }) {
  const [ok, setOk] = useState(false)
  return (
    <button onClick={() => { navigator.clipboard.writeText(text); setOk(true); setTimeout(() => setOk(false), 2000) }}
      className="p-1 rounded hover:bg-neutral-200 transition-colors text-neutral-400">
      {ok ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
    </button>
  )
}

function Message({ msg }) {
  const isUser = msg.role === 'user'
  let text = msg.content
  let jsonBlock = null

  if (!isUser) {
    const m = text.match(/```(?:json)?\s*([\s\S]*?)```/)
    if (m) { jsonBlock = m[1].trim(); text = text.replace(m[0], '').trim() }
    else {
      const jm = text.match(/(\{[\s\S]*\})/)
      if (jm) { try { JSON.parse(jm[1]); jsonBlock = jm[1]; text = text.replace(jm[1], '').trim() } catch {} }
    }
  }

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : ''}`}>
      {!isUser && <div className="w-7 h-7 rounded-lg bg-neutral-900 flex items-center justify-center flex-shrink-0 mt-0.5"><span className="text-white text-[10px] font-bold">AI</span></div>}
      <div className="max-w-[80%]">
        <div className={`rounded-2xl px-4 py-2.5 text-[13px] leading-relaxed tracking-[-0.2px] ${isUser ? 'bg-neutral-900 text-white rounded-br-md' : 'bg-white border border-neutral-200/60 text-neutral-700 rounded-bl-md'}`}>
          {text && <p className="whitespace-pre-wrap">{text}</p>}
        </div>
        {jsonBlock && (
          <div className="mt-2 rounded-xl border border-neutral-200/60 overflow-hidden">
            <div className="flex items-center justify-between px-3 py-1.5 bg-neutral-50 border-b border-neutral-100">
              <span className="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">JSON</span>
              <CopyBtn text={jsonBlock} />
            </div>
            <pre className="p-3 text-[11px] font-mono text-neutral-600 overflow-x-auto bg-white max-h-60 overflow-y-auto">
              {(() => { try { return JSON.stringify(JSON.parse(jsonBlock), null, 2) } catch { return jsonBlock } })()}
            </pre>
          </div>
        )}
      </div>
      {isUser && <div className="w-7 h-7 rounded-lg bg-neutral-200 flex items-center justify-center flex-shrink-0 mt-0.5"><span className="text-neutral-600 text-[10px] font-bold">You</span></div>}
    </div>
  )
}

export default function ChatBar({ documentName, extraction, validation, compliance }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const endRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const send = async (text) => {
    if (!text.trim() || streaming) return
    const userMsg = { role: 'user', content: text.trim() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setStreaming(true)

    const fd = new FormData()
    fd.append('message', text.trim())
    if (documentName) fd.append('sample_name', documentName)
    if (extraction) fd.append('extraction_data', JSON.stringify(extraction))
    if (validation) fd.append('validation_data', JSON.stringify(validation))
    if (compliance) fd.append('compliance_data', JSON.stringify(compliance))
    fd.append('history', JSON.stringify([...messages, userMsg]))

    try {
      const res = await fetch('/api/chat', { method: 'POST', body: fd })
      const reader = res.body.getReader()
      const dec = new TextDecoder()
      let buf = '', full = ''
      setMessages(prev => [...prev, { role: 'assistant', content: '' }])

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += dec.decode(value, { stream: true })
        const lines = buf.split('\n'); buf = lines.pop() || ''
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const d = JSON.parse(line.slice(6))
              if (d.chunk) { full += d.chunk; setMessages(prev => { const u = [...prev]; u[u.length-1] = { role: 'assistant', content: full }; return u }) }
              if (d.done && d.full_response) { setMessages(prev => { const u = [...prev]; u[u.length-1] = { role: 'assistant', content: d.full_response }; return u }) }
              if (d.error) { setMessages(prev => { const u = [...prev]; u[u.length-1] = { role: 'assistant', content: `Error: ${d.error}` }; return u }) }
            } catch {}
          }
        }
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }])
    } finally { setStreaming(false); inputRef.current?.focus() }
  }

  return (
    <div className="glass rounded-2xl overflow-hidden flex flex-col mt-6 max-w-[1320px] mx-auto">
      <div className="px-4 py-3 border-b border-black/[0.04] flex items-center justify-between">
        <span className="text-[13px] font-medium text-neutral-700 tracking-[-0.2px]">Document Chat</span>
        <span className="text-[11px] text-neutral-400 tracking-[-0.2px]">Powered by Strands Agents SDK</span>
      </div>

      {messages.length === 0 && (
        <div className="p-4 border-b border-neutral-100/50">
          <div className="flex items-center gap-1.5 mb-3">
            <Sparkles className="w-3 h-3 text-neutral-400" />
            <span className="text-[11px] font-medium text-neutral-400 tracking-[-0.2px]">Try these</span>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
            {PROMPTS.map(p => (
              <button key={p.label} onClick={() => send(p.prompt)}
                className="text-left p-3 rounded-xl border border-neutral-200/60 bg-white hover:border-neutral-300 hover-lift">
                <span className="text-[12px] font-medium text-neutral-700 tracking-[-0.2px]">{p.label}</span>
                <p className="text-[10px] text-neutral-400 mt-1 line-clamp-2 tracking-[-0.2px]">{p.prompt}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {messages.length > 0 && (
        <div className="flex-1 overflow-y-auto p-4 space-y-3 max-h-[400px]">
          {messages.map((m, i) => <Message key={i} msg={m} />)}
          {streaming && messages[messages.length-1]?.content === '' && (
            <div className="flex items-center gap-2 text-[12px] text-neutral-400">
              <Loader2 className="w-3.5 h-3.5 animate-spin" /> Thinking...
            </div>
          )}
          <div ref={endRef} />
        </div>
      )}

      <form onSubmit={(e) => { e.preventDefault(); send(input) }} className="border-t border-black/[0.04] p-3 flex items-center gap-2">
        <input ref={inputRef} value={input} onChange={e => setInput(e.target.value)} disabled={streaming}
          placeholder="Ask about the document..."
          className="flex-1 px-4 py-2.5 rounded-xl bg-neutral-50 border border-neutral-200/60 text-[13px] text-neutral-700 placeholder:text-neutral-400 focus:outline-none focus:border-neutral-400 focus:ring-1 focus:ring-neutral-200 disabled:opacity-50 transition-all tracking-[-0.2px]" />
        <button type="submit" disabled={!input.trim() || streaming}
          className="w-9 h-9 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white flex items-center justify-center transition-colors disabled:opacity-30">
          {streaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </button>
      </form>
    </div>
  )
}
