import { Shield, AlertTriangle, TrendingUp } from 'lucide-react'

function ScoreRing({ score, size = 100 }) {
  const radius = 40
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference
  const color = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444'

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox="0 0 100 100" className="-rotate-90">
        <circle cx="50" cy="50" r={radius} fill="none" stroke="#e2e8f0" strokeWidth="8" />
        <circle
          cx="50" cy="50" r={radius} fill="none"
          stroke={color} strokeWidth="8" strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="score-ring"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold text-slate-800">{score}</span>
        <span className="text-[10px] text-slate-400 uppercase">Score</span>
      </div>
    </div>
  )
}

function ALCOABar({ principle, score, assessment }) {
  const color = score >= 8 ? 'bg-emerald-500' : score >= 5 ? 'bg-amber-500' : 'bg-red-500'
  const bgColor = score >= 8 ? 'bg-emerald-50' : score >= 5 ? 'bg-amber-50' : 'bg-red-50'

  return (
    <div className={`p-2.5 rounded-lg ${bgColor} transition-all`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-semibold text-slate-700 capitalize">{principle}</span>
        <span className="text-xs font-bold text-slate-600">{score}/10</span>
      </div>
      <div className="w-full h-1.5 bg-white/50 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all duration-1000`} style={{ width: `${score * 10}%` }} />
      </div>
      {assessment && (
        <p className="text-[10px] text-slate-500 mt-1 leading-tight">{assessment}</p>
      )}
    </div>
  )
}

function DeviationCard({ deviation }) {
  const severity = deviation.severity || 'minor'
  const colors = {
    minor: 'border-amber-200 bg-amber-50',
    major: 'border-orange-200 bg-orange-50',
    critical: 'border-red-200 bg-red-50',
  }
  const badgeColors = {
    minor: 'bg-amber-100 text-amber-700',
    major: 'bg-orange-100 text-orange-700',
    critical: 'bg-red-100 text-red-700',
  }

  return (
    <div className={`p-3 rounded-lg border ${colors[severity]}`}>
      <div className="flex items-center gap-2 mb-1">
        <AlertTriangle className={`w-3.5 h-3.5 ${severity === 'critical' ? 'text-red-600' : severity === 'major' ? 'text-orange-600' : 'text-amber-600'}`} />
        <span className="text-xs font-semibold text-slate-700">{deviation.field || deviation.type}</span>
        <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${badgeColors[severity]}`}>
          {severity}
        </span>
      </div>
      <p className="text-xs text-slate-600">{deviation.description}</p>
    </div>
  )
}

export default function ComplianceDashboard({ data }) {
  if (!data) return null

  const scores = data.alcoa_scores || {}
  const overallScore = data.overall_score || 0
  const riskLevel = data.risk_level || 'unknown'
  const deviations = data.deviations || []

  const riskColors = {
    low: 'bg-emerald-100 text-emerald-700',
    medium: 'bg-amber-100 text-amber-700',
    high: 'bg-orange-100 text-orange-700',
    critical: 'bg-red-100 text-red-700',
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2">
        <Shield className="w-4 h-4 text-teal-600" />
        <span className="text-sm font-semibold text-slate-700">ALCOA+ Compliance</span>
        <span className={`ml-auto text-xs font-bold uppercase px-2 py-0.5 rounded-full ${riskColors[riskLevel] || riskColors.medium}`}>
          {riskLevel} risk
        </span>
      </div>

      <div className="p-4 space-y-5">
        {/* Score + summary row */}
        <div className="flex items-center gap-6">
          <ScoreRing score={overallScore} />
          <div className="flex-1">
            <h4 className="text-lg font-bold text-slate-800">
              {overallScore >= 80 ? 'Compliant' : overallScore >= 60 ? 'Needs Review' : 'Non-Compliant'}
            </h4>
            <p className="text-xs text-slate-500 mt-1">{data.recommendation || ''}</p>
            {deviations.length > 0 && (
              <div className="flex items-center gap-1 mt-2 text-xs text-amber-600 font-medium">
                <AlertTriangle className="w-3.5 h-3.5" />
                {deviations.length} deviation{deviations.length > 1 ? 's' : ''} detected
              </div>
            )}
          </div>
        </div>

        {/* ALCOA+ bars */}
        <div>
          <h5 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <TrendingUp className="w-3.5 h-3.5" />
            ALCOA+ Principles
          </h5>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {Object.entries(scores).map(([key, val]) => (
              <ALCOABar key={key} principle={key} score={val.score} assessment={val.assessment} />
            ))}
          </div>
        </div>

        {/* Deviations */}
        {deviations.length > 0 && (
          <div>
            <h5 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5" />
              Deviations
            </h5>
            <div className="space-y-2">
              {deviations.map((d, i) => (
                <DeviationCard key={i} deviation={d} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
