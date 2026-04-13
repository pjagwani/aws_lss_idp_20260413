import { CheckCircle, XCircle, Loader2, ArrowLeft, Clock } from 'lucide-react'

const STAGE_META = {
  extraction: { label: 'Extraction', desc: 'Reading handwritten fields' },
  validation: { label: 'Validation', desc: 'Checking data integrity' },
  compliance: { label: 'Compliance', desc: 'ALCOA+ scoring' },
}

function StageNode({ stageKey, data, index, total }) {
  const meta = STAGE_META[stageKey]
  const status = data?.status || 'pending'

  return (
    <div className="flex items-center">
      <div className="flex flex-col items-center gap-2 min-w-[120px]">
        {/* Circle */}
        <div className={`
          w-11 h-11 rounded-full flex items-center justify-center transition-all duration-500
          ${status === 'pending' ? 'bg-neutral-100 text-neutral-400' : ''}
          ${status === 'running' ? 'bg-neutral-900 text-white pulse-soft' : ''}
          ${status === 'complete' ? 'bg-emerald-500 text-white' : ''}
          ${status === 'error' ? 'bg-red-500 text-white' : ''}
        `}>
          {status === 'complete' ? <CheckCircle className="w-5 h-5" /> :
           status === 'error' ? <XCircle className="w-5 h-5" /> :
           status === 'running' ? <Loader2 className="w-5 h-5 animate-spin" /> :
           <span className="text-[13px] font-semibold">{index + 1}</span>}
        </div>
        <div className="text-center">
          <p className={`text-[13px] font-medium tracking-[-0.3px] ${
            status === 'running' ? 'text-neutral-900' :
            status === 'complete' ? 'text-emerald-700' : 'text-neutral-500'
          }`}>{meta.label}</p>
          <p className="text-[11px] text-neutral-400 mt-0.5 tracking-[-0.2px]">
            {data?.message || meta.desc}
          </p>
        </div>
      </div>

      {index < total - 1 && (
        <div className={`w-16 h-px mx-2 mt-[-24px] transition-colors duration-500 ${
          status === 'complete' ? 'bg-emerald-400' : 'bg-neutral-200'
        }`} />
      )}
    </div>
  )
}

export default function PipelineView({ stages, stageData, pipelineState, duration, error, onReset }) {
  return (
    <div className="mt-8 max-w-[800px] mx-auto">
      <div className="glass rounded-2xl p-6">
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={onReset}
            className="flex items-center gap-1.5 text-[13px] text-neutral-500 hover:text-neutral-800 transition-colors tracking-[-0.2px]"
          >
            <ArrowLeft className="w-4 h-4" />
            New document
          </button>
          <div className="flex items-center gap-3">
            {duration && (
              <span className="flex items-center gap-1 text-[12px] text-neutral-400">
                <Clock className="w-3.5 h-3.5" />
                {duration}s
              </span>
            )}
            <span className={`px-3 py-1 rounded-full text-[11px] font-semibold uppercase tracking-wider ${
              pipelineState === 'running' ? 'bg-neutral-900 text-white pulse-soft' :
              pipelineState === 'complete' ? 'bg-emerald-50 text-emerald-700' :
              'bg-red-50 text-red-700'
            }`}>
              {pipelineState === 'running' ? 'Processing' : pipelineState === 'complete' ? 'Complete' : 'Error'}
            </span>
          </div>
        </div>

        <div className="flex items-start justify-center py-2">
          {stages.map((key, i) => (
            <StageNode key={key} stageKey={key} data={stageData[key]} index={i} total={stages.length} />
          ))}
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-xl bg-red-50 border border-red-100 text-[13px] text-red-700 tracking-[-0.2px]">
            {error}
          </div>
        )}
      </div>
    </div>
  )
}
