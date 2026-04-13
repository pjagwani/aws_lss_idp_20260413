import { useState, useEffect, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, ArrowRight } from 'lucide-react'

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

  const getDifficulty = (name) => {
    if (name.includes('01') || name.includes('clean')) return { label: 'Clean', color: 'text-emerald-600 bg-emerald-50' }
    if (name.includes('02') || name.includes('messy')) return { label: 'Messy', color: 'text-amber-600 bg-amber-50' }
    if (name.includes('03') || name.includes('partial')) return { label: 'Partial', color: 'text-orange-600 bg-orange-50' }
    return { label: 'Challenge', color: 'text-red-600 bg-red-50' }
  }

  return (
    <div className="max-w-[800px] mx-auto pt-20 pb-12">
      {/* Hero text — joindex style: big serif + subtle body */}
      <div className="text-center mb-12">
        <h2 className="font-[DM_Serif_Display] text-[clamp(2rem,4.5vw,48px)] font-normal tracking-[-2px] text-neutral-950 leading-[1.1]">
          Extract structured data from<br />handwritten pharma documents
        </h2>
        <p className="mt-4 text-[16px] text-neutral-400 tracking-[-0.3px] leading-relaxed max-w-lg mx-auto">
          Three AI agents extract, validate, and score your batch records
          for ALCOA+ compliance — powered by Amazon Bedrock.
        </p>
      </div>

      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`
          glass rounded-2xl p-10 cursor-pointer group transition-all duration-200 hover-lift
          ${isDragActive ? 'ring-2 ring-neutral-400 ring-offset-2' : ''}
        `}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-4 text-center">
          <div className={`
            w-12 h-12 rounded-xl flex items-center justify-center transition-colors
            ${isDragActive ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-500 group-hover:bg-neutral-200'}
          `}>
            <Upload className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[15px] font-medium text-neutral-700 tracking-[-0.3px]">
              {isDragActive ? 'Drop your document here' : 'Drop a document here, or click to browse'}
            </p>
            <p className="text-[13px] text-neutral-400 mt-1 tracking-[-0.2px]">
              PDF, PNG, or JPG — Batch Manufacturing Records, QC Forms
            </p>
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="flex items-center gap-4 my-8">
        <div className="flex-1 h-px bg-neutral-200" />
        <span className="text-[11px] font-medium text-neutral-400 uppercase tracking-widest">or choose a sample</span>
        <div className="flex-1 h-px bg-neutral-200" />
      </div>

      {/* Sample cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-24 rounded-xl bg-neutral-100 animate-pulse" />
          ))
        ) : (
          samples.map((s) => {
            const { label, color } = getDifficulty(s.name)
            return (
              <button
                key={s.name}
                onClick={() => onProcess(null, s.name)}
                className="glass text-left p-4 rounded-xl hover-lift group"
              >
                <div className="flex items-start justify-between mb-2">
                  <FileText className="w-5 h-5 text-neutral-400" />
                  <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${color}`}>
                    {label}
                  </span>
                </div>
                <p className="text-[13px] font-medium text-neutral-700 tracking-[-0.2px] truncate">{s.name}</p>
                <div className="flex items-center justify-between mt-2">
                  <p className="text-[11px] text-neutral-400">{(s.size / 1024).toFixed(1)} KB</p>
                  <span className="text-[11px] font-medium text-neutral-400 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    Process <ArrowRight className="w-3 h-3" />
                  </span>
                </div>
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}
