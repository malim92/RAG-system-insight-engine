import { useState } from 'react'
import DocumentManager from './components/DocumentManager.jsx'
import Chat from './components/Chat.jsx'

export default function App() {
  // Bumped on every successful upload so Chat can hint that new
  // knowledge is available. Lifting state here is the simplest
  // cross-component communication — no global store needed yet.
  const [knowledgeVersion, setKnowledgeVersion] = useState(0)

  return (
    <div className="app">
      <header className="app-header">
        <h1>InsightEngine</h1>
        <p className="subtitle">Ask your documents — RAG pipeline demo</p>
      </header>
      <main className="app-body">
        <aside className="sidebar">
          <DocumentManager onUploaded={() => setKnowledgeVersion(v => v + 1)} />
        </aside>
        <section className="chat-panel">
          <Chat knowledgeVersion={knowledgeVersion} />
        </section>
      </main>
    </div>
  )
}
