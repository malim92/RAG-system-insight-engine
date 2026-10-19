import { useEffect, useRef, useState } from 'react'
import { askQuestion } from '../api.js'

export default function Chat({ knowledgeVersion }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function send(e) {
    e.preventDefault()
    const question = input.trim()
    if (!question || busy) return

    setInput('')
    setBusy(true)
    // Optimistically render the user's question; the assistant message
    // arrives in one update so React batches the render.
    setMessages(prev => [...prev, { role: 'user', text: question }])

    try {
      const { answer, citations } = await askQuestion(question)
      setMessages(prev => [...prev, { role: 'assistant', text: answer, citations }])
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: '',
        error: err.message,
      }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="chat">
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <h2>Ask anything about your documents</h2>
            <p>
              Answers are grounded in uploaded documents with inline citations.
              The assistant refuses questions it can't support from the corpus.
            </p>
            {knowledgeVersion === 0 && (
              <p className="chat-hint">⬅ Upload a document first.</p>
            )}
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role}`}>
            <div className="message-text">{m.text}</div>

            {m.error && (
              <div className="message-error">
                ⚠ {m.error}
                {m.error.includes('unavailable') || m.error.includes('503')
                  ? ' — the LLM free tier is busy; retry in a few seconds.'
                  : ''}
              </div>
            )}

            {m.citations?.length > 0 && (
              <div className="citations">
                <div className="citations-title">Sources</div>
                {m.citations.map((c, j) => (
                  <div key={j} className="citation">
                    <span className="citation-num">[{j + 1}]</span>
                    <span className="citation-doc">{c.document_id.slice(0, 8)}…</span>
                    <span>page {c.page_number}</span>
                    <span className={`citation-score ${c.score > 0.6 ? 'good' : c.score > 0.45 ? 'mid' : 'weak'}`}>
                      {(c.score * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        {busy && <div className="message assistant typing">Thinking…</div>}
        <div ref={bottomRef} />
      </div>

      <form className="chat-input" onSubmit={send}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask a question about your documents…"
          disabled={busy}
        />
        <button type="submit" disabled={busy || !input.trim()}>
          {busy ? '…' : 'Send'}
        </button>
      </form>
    </div>
  )
}
