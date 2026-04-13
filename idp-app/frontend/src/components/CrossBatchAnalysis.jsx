import { useState } from 'react'
import { TrendingUp, AlertTriangle, Loader2, BarChart3 } from 'lucide-react'

export default function CrossBatchAnalysis({ extraction, filename }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const run = async () => {
    setLoading(true); setError(null)
    const fd = new FormData()
    fd.append('extraction_data', JSON.stringify(extraction))
    fd.append('filename', filename || '')
    try {
      const r = await fetch('/api/cross-batch-analysis', { method: 'POST', body: fd })
      const d = await r.json()
      if (d.error) setError(d.error); else setData(d.result)
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  if (!data && !loading) return (
    <div className="glass rounded-2xl p-6 text-center">
      <BarChart3 className="w-8 h-8 text-neutral-300 mx-auto mb-3" />
      <h4 className="text-[15px] font-medium text-neutral-700 tracking-[-0.3px]">Cross-Batch Anomaly Detection</h4>
      <p className="text-[12px] text-neutral-400 mt-1 mb-4 max-w-sm mx-auto tracking-[-0.2px]">
        Compare this batch against historical extractions to find statistical outliers.
      </p>
      <button onClick={run} className="px-5 py-2 rounded-full bg-neutral-900 text-white text-[13px] font-medium hover:bg-neutral-800 transition-colors">
        Run Analysis
      </button>
      {error && <p className="text-[12px] text-red-600 mt-3">{error}</p>}
    </div>
  )

  if (loading) return (
    <div className="glass rounded-2xl p-8 text-center">
      <Loader2 className="w-6 h-6 animate-spin text-neutral-400 mx-auto mb-2" />
      <p className="text-[13px] text-neutral-500">Analyzing cross-batch patterns...</p>
    </div>
  )

  const anomalies = data?.anomalies || []
  const risk = data?.overall_risk || 'low'
  const riskStyle = { low: 'text-emerald-700 bg-emerald-50', medium: 'text-amber-700 bg-amber-50', high: 'text-orange-700 bg-orange-50', critical: 'text-red-700 bg-red-50' }
  const sevDot = { low: 'bg-emerald-500', medium: 'bg-amber-500', high: 'bg-orange-500', critical: 'bg-red-500' }

  return (
    <div className="glass rounded-2xl overflow-hidden">
      <div className="px-4 py-3 border-b border-black/[0.04] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-neutral-400" />
          <span className="text-[13px] font-medium text-neutral-700 tracking-[-0.2px]">Cross-Batch Analysis</span>
        </div>
        <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${riskStyle[risk]}`}>{risk} risk</span>
      </div>
      <div className="p-4 space-y-3">
        {data?.batch_comparison && (
          <div className="p-3 rounded-lg bg-neutral-50 text-[12px] text-neutral-600 tracking-[-0.2px]">
            Compared against <strong>{data.batch_comparison.compared_against}</strong> previous batches.
            {data.risk_summary && <span className="block mt-1 text-neutral-400">{data.risk_summary}</span>}
          </div>
        )}
        {anomalies.length === 0 ? (
          <p className="text-[13px] text-emerald-600 font-medium text-center py-4">No anomalies detected</p>
        ) : anomalies.map((a, i) => (
          <div key={i} className="p-3 rounded-lg border border-neutral-200/60 bg-white">
            <div className="flex items-center gap-2 mb-1">
              <span className={`w-2 h-2 rounded-full ${sevDot[a.severity] || sevDot.medium}`} />
              <span className="text-[12px] font-medium text-neutral-700">{a.field || a.type}</span>
              {a.deviation_pct && <span className="text-[10px] font-bold text-red-600 ml-auto">{a.deviation_pct > 0 ? '+' : ''}{a.deviation_pct}%</span>}
            </div>
            <p className="text-[11px] text-neutral-500 tracking-[-0.2px]">{a.description}</p>
            {a.current_value && a.historical_average && (
              <div className="flex gap-4 mt-2 text-[10px] text-neutral-400">
                <span>Current: <strong className="text-neutral-600">{a.current_value}</strong></span>
                <span>Historical avg: <strong className="text-neutral-600">{a.historical_average}</strong></span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
