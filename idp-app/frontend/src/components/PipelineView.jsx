import { CheckCircle, XCircle, Loader2, ArrowLeft, Clock, Brain, ShieldCheck, FileSearch } from 'lucide-react'

const STAGE_META = {
  extraction: { label: 'Extraction Agent', icon: FileSearch, desc: 'Reading handwritten fields' },
  validation: { label: 'Validation Agent', icon: Brain, desc: 'Checking data integrity' },
  compliance: { label: 'Compliance Agent', icon: ShieldCheck, desc: 'ALCOA+ scoring' },
}

function StageNode({ stageKey, data, index, total }) {
  const meta = STAGE_META[stageKey]
  const Icon = meta.icon
  const status = data?.status || 'pending'

  const ring = {
    pending: 'border-slate-200 bg-slate-50 text-slate-400',
    running: 'border-teal-500 bg-teal-50 text-teal-600 stage-active',
    complete: 'border-emerald-500 bg-emerald-50 text-emerald-600',
    error: 'border-red-500 bg-red-50 text-red-600',
  }[status]

  return (
    <div className="flex items-center gap-0">
      <div className="flex flex-col items-center gap-2">
        {/* Circle */}
        <div className={`
          relative w-16 h-16 rounded-full border-2 flex items-center justify-center
          transition-all duration-500 ${ring}
        `}>
          {status === 'running' && (
            <div className="absolute inset-0 rounded-full animate-ping bg-teal-400/20" />
          )}
          {status === 'complete' ? (
            <CheckCircle className="w-7 h-7 text-emerald-500" />
          ) : status === 'error' ? (
            <XCircle className="w-7 h-7 text-red-500" />
          ) : status === 'running' ? (
            <Loader2 className="w-7 h-7 animate-spin" />
          ) : (
            <Icon className="w-7 h-7" />
          )}
        </div>

        {/* Label */}
        <div className="text-center">
          <p className={`text-sm font-semibold ${status === 'running' ? 'text-teal-700' : status === 'complete' ? 'text-emerald-700' : 'text-slate-600'}`}>
            {meta.label}
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5">
            {data?.message || meta.desc}
          </p>
        </div>
      </div>

      {/* Connector line */}
      {index < total - 1 && (
        <div className={`
          w-24 h-0.5 mx-4 mt-[-28px] transition-colors duration-500
          ${status === 'complete' ? 'bg-emerald-400' : 'bg-slate-200'}
        `} />
      )}
    </div>
  )
}

export default function PipelineView({ stages, stageData, pipelineState, duration, error, onReset }) {
  return (
    <div className="mt-8">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
        {/* Top bar */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button
              onClick={onReset}
              className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-teal-600 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              New Document
            </button>
          </div>

          <div className="flex items-center gap-4">
            {duration && (
              <span className="flex items-center gap-1.5 text-sm text-slate-500">
                <Clock className="w-4 h-4" />
                {duration}s
              </span>
            )}
            <span className={`
              px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider
              ${pipelineState === 'running' ? 'bg-teal-100 text-teal-700 animate-pulse' : ''}
              ${pipelineState === 'complete' ? 'bg-emerald-100 text-emerald-700' : ''}
              ${pipelineState === 'error' ? 'bg-red-100 text-red-700' : ''}
            `}>
              {pipelineState === 'running' ? 'Processing' : pipelineState === 'complete' ? 'Complete' : 'Error'}
            </span>
          </div>
        </div>

        {/* Stage nodes */}
        <div className="flex items-start justify-center py-4">
          {stages.map((key, i) => (
            <StageNode
              key={key}
              stageKey={key}
              data={stageData[key]}
              index={i}
              total={stages.length}
            />
          ))}
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
            {error}
          </div>
        )}
      </div>
    </div>
  )
}
