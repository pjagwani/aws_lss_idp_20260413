import { useState, useCallback } from 'react'
import Header from './components/Header'
import DocumentUpload from './components/DocumentUpload'
import PipelineView from './components/PipelineView'
import ExtractionResults from './components/ExtractionResults'
import ComplianceDashboard from './components/ComplianceDashboard'
import DocumentViewer from './components/DocumentViewer'
import ChatBar from './components/ChatBar'
import CrossBatchAnalysis from './components/CrossBatchAnalysis'
import DeviationReport from './components/DeviationReport'
import HandwritingScore from './components/HandwritingScore'
import MultiDocReconciliation from './components/MultiDocReconciliation'

const STAGES = ['extraction', 'validation', 'compliance']

const TABS = [
  { id: 'results', label: 'Extraction & Compliance' },
  { id: 'anomaly', label: 'Cross-Batch' },
  { id: 'deviation', label: 'Deviation Report' },
  { id: 'handwriting', label: 'Handwriting' },
]

export default function App() {
  const [document, setDocument] = useState(null)
  const [pipelineState, setPipelineState] = useState('idle')
  const [stages, setStages] = useState({})
  const [error, setError] = useState(null)
  const [duration, setDuration] = useState(null)
  const [activeTab, setActiveTab] = useState('results')
  const [mode, setMode] = useState('pipeline') // pipeline | reconciliation

  const resetPipeline = useCallback(() => {
    setPipelineState('idle')
    setStages({})
    setError(null)
    setDuration(null)
    setActiveTab('results')
  }, [])

  const handleSSE = (eventType, data) => {
    switch (eventType) {
      case 'stage_start':
        setStages(prev => ({ ...prev, [data.stage]: { status: 'running', label: data.label, message: data.message } }))
        break
      case 'stage_complete':
        setStages(prev => ({ ...prev, [data.stage]: { status: 'complete', label: data.label, result: data.result, message: data.message } }))
        break
      case 'stage_error':
        setStages(prev => ({ ...prev, [data.stage]: { status: 'error', error: data.error } }))
        break
      case 'pipeline_complete':
        setPipelineState(data.status === 'success' ? 'complete' : 'error')
        setDuration(data.duration)
        if (data.error) setError(data.error)
        break
    }
  }

  const processDocument = useCallback(async (file, sampleName) => {
    resetPipeline()
    setPipelineState('running')
    setMode('pipeline')

    if (file) {
      setDocument({ name: file.name, url: URL.createObjectURL(file) })
    } else if (sampleName) {
      setDocument({ name: sampleName, url: `/api/samples/${encodeURIComponent(sampleName)}` })
    }

    const formData = new FormData()
    if (file) formData.append('file', file)
    else if (sampleName) formData.append('sample_name', sampleName)

    try {
      const response = await fetch('/api/process', { method: 'POST', body: formData })
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        let eventType = null
        for (const line of lines) {
          if (line.startsWith('event: ')) eventType = line.slice(7).trim()
          else if (line.startsWith('data: ') && eventType) {
            try { handleSSE(eventType, JSON.parse(line.slice(6))) } catch {}
            eventType = null
          }
        }
      }
    } catch (err) { setError(err.message); setPipelineState('error') }
  }, [resetPipeline])

  const extraction = stages.extraction?.result
  const validation = stages.validation?.result
  const compliance = stages.compliance?.result

  return (
    <div className="min-h-screen" style={{ background: '#f4f4f6' }}>
      <Header />

      <main className="pb-12">
        {/* Mode toggle */}
        {pipelineState === 'idle' && (
          <div className="max-w-[1320px] mx-auto px-6 pt-6">
            <div className="flex items-center gap-1 p-1 rounded-full bg-neutral-200/50 w-fit mx-auto">
              <button onClick={() => setMode('pipeline')}
                className={`px-4 py-1.5 rounded-full text-[12px] font-medium transition-all ${mode === 'pipeline' ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-500 hover:text-neutral-700'}`}>
                Single Document
              </button>
              <button onClick={() => setMode('reconciliation')}
                className={`px-4 py-1.5 rounded-full text-[12px] font-medium transition-all ${mode === 'reconciliation' ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-500 hover:text-neutral-700'}`}>
                Multi-Doc Reconciliation
              </button>
            </div>
          </div>
        )}

        {/* Single document mode */}
        {mode === 'pipeline' && pipelineState === 'idle' && (
          <DocumentUpload onProcess={processDocument} />
        )}

        {/* Reconciliation mode */}
        {mode === 'reconciliation' && pipelineState === 'idle' && (
          <MultiDocReconciliation />
        )}

        {/* Pipeline running/complete */}
        {pipelineState !== 'idle' && mode === 'pipeline' && (
          <>
            <div className="max-w-[1320px] mx-auto px-6">
              <PipelineView stages={STAGES} stageData={stages} pipelineState={pipelineState}
                duration={duration} error={error} onReset={() => { resetPipeline(); setDocument(null) }} />
            </div>

            {/* Tab navigation */}
            {extraction && (
              <div className="max-w-[1320px] mx-auto px-6 mt-6">
                <div className="flex items-center gap-1 p-1 rounded-full bg-neutral-200/50 w-fit">
                  {TABS.map(t => (
                    <button key={t.id} onClick={() => setActiveTab(t.id)}
                      className={`px-4 py-1.5 rounded-full text-[12px] font-medium transition-all ${
                        activeTab === t.id ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-500 hover:text-neutral-700'
                      }`}>
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Tab content */}
            {document && (
              <div className="max-w-[1320px] mx-auto px-6 mt-4">
                {activeTab === 'results' && (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <DocumentViewer document={document} />
                    <div className="space-y-6">
                      {extraction && <ExtractionResults data={extraction} validation={validation} />}
                      {compliance && <ComplianceDashboard data={compliance} />}
                    </div>
                  </div>
                )}

                {activeTab === 'anomaly' && extraction && (
                  <CrossBatchAnalysis extraction={extraction} filename={document.name} />
                )}

                {activeTab === 'deviation' && extraction && (
                  <DeviationReport extraction={extraction} validation={validation}
                    compliance={compliance} filename={document.name} />
                )}

                {activeTab === 'handwriting' && extraction && (
                  <HandwritingScore extraction={extraction} filename={document.name} />
                )}
              </div>
            )}

            {/* Chat bar */}
            {extraction && (
              <div className="max-w-[1320px] mx-auto px-6">
                <ChatBar documentName={document?.name} extraction={extraction}
                  validation={validation} compliance={compliance} />
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}
