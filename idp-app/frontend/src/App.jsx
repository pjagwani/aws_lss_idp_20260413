import { useState, useCallback } from 'react'
import Header from './components/Header'
import DocumentUpload from './components/DocumentUpload'
import PipelineView from './components/PipelineView'
import ExtractionResults from './components/ExtractionResults'
import ComplianceDashboard from './components/ComplianceDashboard'
import DocumentViewer from './components/DocumentViewer'
import ChatBar from './components/ChatBar'

const STAGES = ['extraction', 'validation', 'compliance']

export default function App() {
  const [document, setDocument] = useState(null)
  const [pipelineState, setPipelineState] = useState('idle')
  const [stages, setStages] = useState({})
  const [pipelineResult, setPipelineResult] = useState(null)
  const [error, setError] = useState(null)
  const [duration, setDuration] = useState(null)

  const resetPipeline = useCallback(() => {
    setPipelineState('idle')
    setStages({})
    setPipelineResult(null)
    setError(null)
    setDuration(null)
  }, [])

  const handleSSE = (eventType, data) => {
    switch (eventType) {
      case 'stage_start':
        setStages(prev => ({
          ...prev,
          [data.stage]: { status: 'running', label: data.label, message: data.message }
        }))
        break
      case 'stage_complete':
        setStages(prev => ({
          ...prev,
          [data.stage]: { status: 'complete', label: data.label, result: data.result, message: data.message }
        }))
        break
      case 'stage_error':
        setStages(prev => ({
          ...prev,
          [data.stage]: { status: 'error', error: data.error }
        }))
        break
      case 'pipeline_complete':
        setPipelineState(data.status === 'success' ? 'complete' : 'error')
        setPipelineResult(data)
        setDuration(data.duration)
        if (data.error) setError(data.error)
        break
    }
  }

  const processDocument = useCallback(async (file, sampleName) => {
    resetPipeline()
    setPipelineState('running')

    if (file) {
      const url = URL.createObjectURL(file)
      setDocument({ name: file.name, url })
    } else if (sampleName) {
      setDocument({ name: sampleName, url: `/api/samples/${encodeURIComponent(sampleName)}` })
    }

    const formData = new FormData()
    if (file) {
      formData.append('file', file)
    } else if (sampleName) {
      formData.append('sample_name', sampleName)
    }

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
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim()
          } else if (line.startsWith('data: ') && eventType) {
            try {
              const data = JSON.parse(line.slice(6))
              handleSSE(eventType, data)
            } catch {}
            eventType = null
          }
        }
      }
    } catch (err) {
      setError(err.message)
      setPipelineState('error')
    }
  }, [resetPipeline])

  const extraction = stages.extraction?.result
  const validation = stages.validation?.result
  const compliance = stages.compliance?.result

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-teal-50/30 to-emerald-50/20">
      <Header />

      <main className="max-w-[1600px] mx-auto px-6 pb-12">
        {pipelineState === 'idle' && (
          <DocumentUpload onProcess={processDocument} />
        )}

        {pipelineState !== 'idle' && (
          <>
            <PipelineView
              stages={STAGES}
              stageData={stages}
              pipelineState={pipelineState}
              duration={duration}
              error={error}
              onReset={() => { resetPipeline(); setDocument(null); }}
            />

            {document && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
                <div className="space-y-6">
                  <DocumentViewer document={document} />
                </div>
                <div className="space-y-6">
                  {extraction && (
                    <ExtractionResults data={extraction} validation={validation} />
                  )}
                  {compliance && (
                    <ComplianceDashboard data={compliance} />
                  )}
                </div>
              </div>
            )}

            {/* Chat bar — full width below the split pane */}
            {extraction && (
              <ChatBar
                documentName={document?.name}
                extraction={extraction}
                validation={validation}
                compliance={compliance}
              />
            )}
          </>
        )}
      </main>
    </div>
  )
}
