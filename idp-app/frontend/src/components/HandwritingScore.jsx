import { useState } from 'react'
import { PenTool, Loader2 } from 'lucide-react'

function GradeRing({ grade, score }) {
  const colors = { A: '#10b981', B: '#34d399', C: '#f59e0b', D: '#f97316', F: '#ef4444' }
  const color = colors[grade] || colors.C
  const r = 32, c = 2 * Math.PI * r, offset = c - (score / 100) * c

  return (
    <div className="relative w-[80px] h-[80px]">
      <svg width="80" height="80" viewBox="0 0 80 80" className="-rotate-90">
        <circle cx="40" cy="40" r={r} fill="none" stroke="#e5e7eb" strokeWidth="5" />
        <circle cx="40" cy="40" r={r} fill="none" stroke={color} strokeWidth="5"
          strokeLinecap="round" strokeDasharray={c} strokeDashoffset={offset} className="score-ring" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold text-neutral-900">{grade}</span>
        <span className="text-[9px] text-neutral-400">{score}/100</span>
      </div>
    </div>
  )
}

export default function HandwritingScore({ extraction, filename }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const run = async () => {
    setLoading(true); setError(null)
    const fd = new FormData()
    fd.append('extraction_data', JSON.stringify(extraction))
    fd.append('filename', filename || '')
    try {
      const r = await fetch('/api/handwriting-score', { method: 'POST', body: fd })
      const d = await r.json()
      if (d.error) setError(d.error); else setData(d.result)
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  if (!data && !loading) return (
    <div className="glass rounded-2xl p-6 text-center">
      <PenTool className="w-8 h-8 text-neutral-300 mx-auto mb-3" />
      <h4 className="text-[15px] font-medium text-neutral-700 tracking-[-0.3px]">Handwriting Quality Score</h4>
      <p className="text-[12px] text-neutral-400 mt-1 mb-4 max-w-sm mx-auto tracking-[-0.2px]">
        Assess operator handwriting legibility and get training recommendations.
      </p>
      <button onClick={run} className="px-5 py-2 rounded-full bg-neutral-900 text-white text-[13px] font-medium hover:bg-neutral-800 transition-colors">
        Score Handwriting
      </button>
      {error && <p className="text-[12px] text-red-600 mt-3">{error}</p>}
    </div>
  )

  if (loading) return (
    <div className="glass rounded-2xl p-8 text-center">
      <Loader2 className="w-6 h-6 animate-spin text-neutral-400 mx-auto mb-2" />
      <p className="text-[13px] text-neutral-500">Scoring handwriting quality...</p>
    </div>
  )

  const fields = data?.field_scores || []
  const recs = data?.training_recommendations || []
  const riskStyle = { low: 'text-emerald-700 bg-emerald-50', medium: 'text-amber-700 bg-amber-50', high: 'text-red-700 bg-red-50' }

  return (
    <div className="glass rounded-2xl overflow-hidden">
      <div className="px-4 py-3 border-b border-black/[0.04] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <PenTool className="w-4 h-4 text-neutral-400" />
          <span className="text-[13px] font-medium text-neutral-700 tracking-[-0.2px]">Handwriting Quality</span>
        </div>
        <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${riskStyle[data?.risk_level] || riskStyle.low}`}>
          {data?.risk_level || 'low'} risk
        </span>
      </div>

      <div className="p-4 space-y-4">
        {/* Score + operator */}
        <div className="flex items-center gap-5">
          <GradeRing grade={data?.grade || 'C'} score={data?.overall_score || 0} />
          <div>
            <p className="text-[11px] text-neutral-400 uppercase tracking-wider">Operator</p>
            <p className="text-[18px] font-bold text-neutral-900 tracking-[-0.5px]">{data?.operator || '—'}</p>
            {data?.comparison_note && <p className="text-[11px] text-neutral-400 mt-1">{data.comparison_note}</p>}
          </div>
        </div>

        {/* Strengths / Weaknesses */}
        {data?.trends && (
          <div className="grid grid-cols-2 gap-2">
            <div className="p-2.5 rounded-lg bg-emerald-50">
              <p className="text-[10px] font-semibold text-emerald-600 uppercase tracking-widest mb-1">Strengths</p>
              {(data.trends.strengths || []).map((s, i) => (
                <p key={i} className="text-[11px] text-emerald-700">{s}</p>
              ))}
            </div>
            <div className="p-2.5 rounded-lg bg-amber-50">
              <p className="text-[10px] font-semibold text-amber-600 uppercase tracking-widest mb-1">Weaknesses</p>
              {(data.trends.weaknesses || []).map((w, i) => (
                <p key={i} className="text-[11px] text-amber-700">{w}</p>
              ))}
            </div>
          </div>
        )}

        {/* Field scores */}
        {fields.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-2">Field Legibility</p>
            <div className="space-y-1">
              {fields.map((f, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span className="text-[11px] text-neutral-500 w-28 truncate">{f.field}</span>
                  <div className="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full transition-all duration-700 ${f.legibility_score >= 80 ? 'bg-emerald-500' : f.legibility_score >= 50 ? 'bg-amber-500' : 'bg-red-500'}`}
                      style={{ width: `${f.legibility_score}%` }} />
                  </div>
                  <span className="text-[10px] font-bold text-neutral-500 w-8 text-right">{f.legibility_score}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recommendations */}
        {recs.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-2">Training Recommendations</p>
            <div className="space-y-1">
              {recs.map((r, i) => (
                <div key={i} className="flex items-start gap-2 p-2 rounded-lg bg-neutral-50">
                  <span className="text-[10px] font-bold text-neutral-400 mt-0.5">{i + 1}.</span>
                  <p className="text-[12px] text-neutral-600 tracking-[-0.2px]">{r}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
