import { AlertTriangle } from 'lucide-react'

function ScoreRing({ score, size = 90 }) {
  const r = 36, c = 2 * Math.PI * r
  const offset = c - (score / 100) * c
  const color = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444'

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox="0 0 90 90" className="-rotate-90">
        <circle cx="45" cy="45" r={r} fill="none" stroke="#e5e7eb" strokeWidth="6" />
        <circle cx="45" cy="45" r={r} fill="none" stroke={color} strokeWidth="6"
          strokeLinecap="round" strokeDasharray={c} strokeDashoffset={offset} className="score-ring" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-xl font-bold text-neutral-900 tracking-[-0.5px]">{score}</span>
        <span className="text-[9px] text-neutral-400 uppercase tracking-wider">Score</span>
      </div>
    </div>
  )
}

function Bar({ principle, score, assessment }) {
  const bg = score >= 8 ? 'bg-emerald-50' : score >= 5 ? 'bg-amber-50' : 'bg-red-50'
  const fill = score >= 8 ? 'bg-emerald-500' : score >= 5 ? 'bg-amber-500' : 'bg-red-500'

  return (
    <div className={`p-2.5 rounded-lg ${bg}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-[11px] font-medium text-neutral-600 capitalize tracking-[-0.2px]">{principle}</span>
        <span className="text-[11px] font-bold text-neutral-500">{score}/10</span>
      </div>
      <div className="w-full h-1 bg-white/60 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${fill} transition-all duration-1000`} style={{ width: `${score * 10}%` }} />
      </div>
      {assessment && <p className="text-[10px] text-neutral-400 mt-1 leading-tight tracking-[-0.2px]">{assessment}</p>}
    </div>
  )
}

function Deviation({ d }) {
  const sev = d.severity || 'minor'
  const border = { minor: 'border-amber-200', major: 'border-orange-200', critical: 'border-red-200' }
  const badge = { minor: 'bg-amber-50 text-amber-700', major: 'bg-orange-50 text-orange-700', critical: 'bg-red-50 text-red-700' }

  return (
    <div className={`p-3 rounded-lg border ${border[sev]} bg-white`}>
      <div className="flex items-center gap-2 mb-1">
        <AlertTriangle className="w-3 h-3 text-amber-500" />
        <span className="text-[11px] font-medium text-neutral-700">{d.field || d.type}</span>
        <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${badge[sev]}`}>{sev}</span>
      </div>
      <p className="text-[11px] text-neutral-500 tracking-[-0.2px]">{d.description}</p>
    </div>
  )
}

export default function ComplianceDashboard({ data }) {
  if (!data) return null
  const scores = data.alcoa_scores || {}
  const overall = data.overall_score || 0
  const risk = data.risk_level || 'unknown'
  const deviations = data.deviations || []

  const riskStyle = { low: 'text-emerald-700 bg-emerald-50', medium: 'text-amber-700 bg-amber-50', high: 'text-orange-700 bg-orange-50', critical: 'text-red-700 bg-red-50' }

  return (
    <div className="glass rounded-2xl overflow-hidden">
      <div className="px-4 py-3 border-b border-black/[0.04] flex items-center justify-between">
        <span className="text-[13px] font-medium text-neutral-700 tracking-[-0.2px]">ALCOA+ Compliance</span>
        <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${riskStyle[risk] || riskStyle.medium}`}>
          {risk} risk
        </span>
      </div>

      <div className="p-4 space-y-5">
        {/* Score + summary */}
        <div className="flex items-center gap-5">
          <ScoreRing score={overall} />
          <div className="flex-1">
            <h4 className="text-[16px] font-semibold text-neutral-900 tracking-[-0.3px]">
              {overall >= 80 ? 'Compliant' : overall >= 60 ? 'Needs Review' : 'Non-Compliant'}
            </h4>
            <p className="text-[12px] text-neutral-400 mt-1 tracking-[-0.2px] leading-relaxed">{data.recommendation || ''}</p>
            {deviations.length > 0 && (
              <p className="text-[11px] text-amber-600 font-medium mt-1.5 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                {deviations.length} deviation{deviations.length > 1 ? 's' : ''} found
              </p>
            )}
          </div>
        </div>

        {/* ALCOA+ bars */}
        <div>
          <p className="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-2">Principles</p>
          <div className="grid grid-cols-2 gap-1.5">
            {Object.entries(scores).map(([k, v]) => <Bar key={k} principle={k} score={v.score} assessment={v.assessment} />)}
          </div>
        </div>

        {/* Deviations */}
        {deviations.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-2">Deviations</p>
            <div className="space-y-1.5">{deviations.map((d, i) => <Deviation key={i} d={d} />)}</div>
          </div>
        )}
      </div>
    </div>
  )
}
