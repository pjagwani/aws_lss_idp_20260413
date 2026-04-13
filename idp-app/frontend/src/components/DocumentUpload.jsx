import { useState, useEffect, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, FlaskConical, ArrowRight, Sparkles } from 'lucide-react'

export default function DocumentUpload({ onProcess }) {
  const [samples, setSamples] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/samples')
      .then(r => r.json())
      .then(d => { setSamples(d.samples || []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const onDrop = useCallback((files) => {
    if (files[0]) onProcess(files[0], null)
  }, [onProcess])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'], 'image/png': ['.png'], 'image/jpeg': ['.jpg', '.jpeg'] },
    maxFiles: 1,
  })

  return (
    <div className="mt-8 space-y-8">
      {/* Hero */}
      <div className="text-center max-w-2xl mx-auto">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-teal-100 text-teal-800 text-sm font-medium mb-4">
          <Sparkles className="w-4 h-4" />
          Multi-Agent AI Pipeline
        </div>
        <h2 className="text-3xl font-bold text-slate-800 tracking-tight">
          Upload a pharmaceutical document
        </h2>
        <p className="mt-2 text-slate-500">
          Three specialized agents extract, validate, and score your batch records for ALCOA+ compliance in real-time.
        </p>
      </div>

      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`
          relative max-w-2xl mx-auto rounded-2xl border-2 border-dashed p-12
          transition-all duration-200 cursor-pointer group
          ${isDragActive
            ? 'border-teal-500 bg-teal-50 scale-[1.02]'
            : 'border-slate-300 bg-white hover:border-teal-400 hover:bg-teal-50/50'}
        `}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-4 text-center">
          <div className={`
            w-16 h-16 rounded-2xl flex items-center justify-center
            transition-colors duration-200
            ${isDragActive ? 'bg-teal-500 text-white' : 'bg-teal-100 text-teal-600 group-hover:bg-teal-200'}
          `}>
            <Upload className="w-8 h-8" />
          </div>
          <div>
            <p className="text-lg font-semibold text-slate-700">
              {isDragActive ? 'Drop your document here' : 'Drag & drop a document'}
            </p>
            <p className="text-sm text-slate-400 mt-1">
              PDF, PNG, or JPG &mdash; Batch Manufacturing Records, QC Forms
            </p>
          </div>
        </div>
      </div>

      {/* OR divider */}
      <div className="flex items-center gap-4 max-w-2xl mx-auto">
        <div className="flex-1 h-px bg-slate-200" />
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">or choose a sample</span>
        <div className="flex-1 h-px bg-slate-200" />
      </div>

      {/* Sample cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 max-w-4xl mx-auto">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-32 rounded-xl bg-slate-100 animate-pulse" />
          ))
        ) : (
          samples.map((s) => {
            const isClean = s.name.includes('01') || s.name.includes('clean')
            const isMessy = s.name.includes('02') || s.name.includes('messy')
            const isPartial = s.name.includes('03') || s.name.includes('partial')
            const difficulty = isClean ? 'Easy' : isMessy ? 'Medium' : isPartial ? 'Hard' : 'Challenge'
            const color = isClean ? 'emerald' : isMessy ? 'amber' : isPartial ? 'orange' : 'red'

            return (
              <button
                key={s.name}
                onClick={() => onProcess(null, s.name)}
                className="group text-left p-4 rounded-xl bg-white border border-slate-200
                           hover:border-teal-300 hover:shadow-lg hover:shadow-teal-100/50
                           transition-all duration-200"
              >
                <div className="flex items-start justify-between mb-3">
                  <FileText className="w-8 h-8 text-teal-500" />
                  <span className={`
                    text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full
                    ${color === 'emerald' ? 'bg-emerald-100 text-emerald-700' : ''}
                    ${color === 'amber' ? 'bg-amber-100 text-amber-700' : ''}
                    ${color === 'orange' ? 'bg-orange-100 text-orange-700' : ''}
                    ${color === 'red' ? 'bg-red-100 text-red-700' : ''}
                  `}>
                    {difficulty}
                  </span>
                </div>
                <p className="text-sm font-semibold text-slate-700 truncate">{s.name}</p>
                <p className="text-xs text-slate-400 mt-1">{(s.size / 1024).toFixed(1)} KB</p>
                <div className="mt-3 flex items-center gap-1 text-xs font-medium text-teal-600 opacity-0 group-hover:opacity-100 transition-opacity">
                  Process <ArrowRight className="w-3 h-3" />
                </div>
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}
