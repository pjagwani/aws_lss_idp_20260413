import { useState, useRef, useEffect } from 'react'
import { Send, MessageSquare, Sparkles, Loader2, Bot, User, Copy, Check } from 'lucide-react'

const SUGGESTED_PROMPTS = [
  {
    label: 'Extract All Fields',
    prompt: 'Extract all handwritten fields from this document and return the results as structured JSON, including product name, batch number, ingredient names, weights, lot numbers, equipment IDs, operator initials, and timestamps.',
  },
  {
    label: 'Ingredients Only',
    prompt: 'Extract only the ingredient names and their corresponding weights in kg. Return the results as a JSON array of objects with "ingredient_name" and "weight_kg" fields.',
  },
  {
    label: 'Validate Batch #',
    prompt: 'Extract the batch number and operator initials. The expected batch number is "BMR-2024-0847" and the expected operator initials are "JKL". Compare your extracted values against these expected values and report whether each field matches.',
  },
  {
    label: 'Compliance Summary',
    prompt: 'Provide a compliance summary for this batch record. Identify any ALCOA+ violations, missing required fields, and recommend corrective actions.',
  },
]

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button onClick={handleCopy} className="p-1 rounded hover:bg-slate-200 transition-colors text-slate-400 hover:text-slate-600">
      {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  )
}

function ChatMessage({ message }) {
  const isUser = message.role === 'user'
  const hasJson = message.content.includes('{') && message.content.includes('}')

  // Try to detect and format JSON blocks
  let formattedContent = message.content
  let jsonBlock = null
  if (!isUser && hasJson) {
    const match = message.content.match(/```(?:json)?\s*([\s\S]*?)```/)
    if (match) {
      jsonBlock = match[1].trim()
      formattedContent = message.content.replace(/```(?:json)?\s*[\s\S]*?```/, '').trim()
    } else {
      // Try to find raw JSON
      const jsonMatch = message.content.match(/(\{[\s\S]*\})/)
      if (jsonMatch) {
        try {
          JSON.parse(jsonMatch[1])
          jsonBlock = jsonMatch[1]
          formattedContent = message.content.replace(jsonMatch[1], '').trim()
        } catch {}
      }
    }
  }

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : ''}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-lg bg-teal-100 flex items-center justify-center flex-shrink-0 mt-0.5">
          <Bot className="w-4 h-4 text-teal-700" />
        </div>
      )}
      <div className={`max-w-[80%] ${isUser ? 'order-first' : ''}`}>
        <div className={`
          rounded-2xl px-4 py-2.5 text-sm leading-relaxed
          ${isUser
            ? 'bg-teal-600 text-white rounded-br-md'
            : 'bg-slate-100 text-slate-700 rounded-bl-md'}
        `}>
          {formattedContent && <p className="whitespace-pre-wrap">{formattedContent}</p>}
        </div>
        {jsonBlock && (
          <div className="mt-2 rounded-xl border border-slate-200 overflow-hidden">
            <div className="flex items-center justify-between px-3 py-1.5 bg-slate-50 border-b border-slate-200">
              <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">JSON Output</span>
              <CopyButton text={jsonBlock} />
            </div>
            <pre className="p-3 text-xs font-mono text-slate-700 overflow-x-auto bg-white max-h-64 overflow-y-auto">
              {(() => { try { return JSON.stringify(JSON.parse(jsonBlock), null, 2) } catch { return jsonBlock } })()}
            </pre>
          </div>
        )}
      </div>
      {isUser && (
        <div className="w-8 h-8 rounded-lg bg-teal-600 flex items-center justify-center flex-shrink-0 mt-0.5">
          <User className="w-4 h-4 text-white" />
        </div>
      )}
    </div>
  )
}

export default function ChatBar({ documentName, extraction, validation, compliance }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text) => {
    if (!text.trim() || isStreaming) return

    const userMsg = { role: 'user', content: text.trim() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setIsStreaming(true)

    const formData = new FormData()
    formData.append('message', text.trim())
    if (documentName) formData.append('sample_name', documentName)
    if (extraction) formData.append('extraction_data', JSON.stringify(extraction))
    if (validation) formData.append('validation_data', JSON.stringify(validation))
    if (compliance) formData.append('compliance_data', JSON.stringify(compliance))
    formData.append('history', JSON.stringify([...messages, userMsg]))

    try {
      const response = await fetch('/api/chat', { method: 'POST', body: formData })
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullResponse = ''

      // Add placeholder assistant message
      setMessages(prev => [...prev, { role: 'assistant', content: '' }])

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.chunk) {
                fullResponse += data.chunk
                setMessages(prev => {
                  const updated = [...prev]
                  updated[updated.length - 1] = { role: 'assistant', content: fullResponse }
                  return updated
                })
              }
              if (data.done && data.full_response) {
                setMessages(prev => {
                  const updated = [...prev]
                  updated[updated.length - 1] = { role: 'assistant', content: data.full_response }
                  return updated
                })
              }
              if (data.error) {
                setMessages(prev => {
                  const updated = [...prev]
                  updated[updated.length - 1] = { role: 'assistant', content: `Error: ${data.error}` }
                  return updated
                })
              }
            } catch {}
          }
        }
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }])
    } finally {
      setIsStreaming(false)
      inputRef.current?.focus()
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    sendMessage(input)
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col mt-6">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2">
        <MessageSquare className="w-4 h-4 text-teal-600" />
        <span className="text-sm font-semibold text-slate-700">Document Chat</span>
        <span className="text-xs text-slate-400 ml-auto">Ask follow-up questions about the extracted data</span>
      </div>

      {/* Suggested prompts (only when no messages) */}
      {messages.length === 0 && (
        <div className="p-4 border-b border-slate-50">
          <div className="flex items-center gap-1.5 mb-3">
            <Sparkles className="w-3.5 h-3.5 text-teal-500" />
            <span className="text-xs font-medium text-slate-500">Suggested prompts</span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {SUGGESTED_PROMPTS.map((sp) => (
              <button
                key={sp.label}
                onClick={() => sendMessage(sp.prompt)}
                className="text-left p-3 rounded-xl border border-slate-200 hover:border-teal-300
                           hover:bg-teal-50/50 transition-all group"
              >
                <span className="text-xs font-semibold text-teal-700 group-hover:text-teal-800">{sp.label}</span>
                <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{sp.prompt}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      {messages.length > 0 && (
        <div className="flex-1 overflow-y-auto p-4 space-y-4 max-h-[400px]">
          {messages.map((msg, i) => (
            <ChatMessage key={i} message={msg} />
          ))}
          {isStreaming && messages[messages.length - 1]?.content === '' && (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              Thinking...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="border-t border-slate-100 p-3 flex items-center gap-2">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about the document — e.g. 'Extract only ingredients as JSON'"
          disabled={isStreaming}
          className="flex-1 px-4 py-2.5 rounded-xl bg-slate-50 border border-slate-200
                     text-sm text-slate-700 placeholder:text-slate-400
                     focus:outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-100
                     disabled:opacity-50 transition-all"
        />
        <button
          type="submit"
          disabled={!input.trim() || isStreaming}
          className="w-10 h-10 rounded-xl bg-teal-600 hover:bg-teal-700 text-white
                     flex items-center justify-center transition-colors
                     disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {isStreaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </button>
      </form>
    </div>
  )
}
