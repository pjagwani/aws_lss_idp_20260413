import { useState } from 'react'
import { FileWarning, Loader2, Copy, Check, ChevronDown, ChevronRight } from 'lucide-react'

function CopyBtn({ text }) {
  const [ok, setOk] = useState(false)
  return (
    <button onClick={() => { navigator.clipboard.writeText(text); setOk(true); setTimeout(() => setOk(false), 2000) }}
      className="p-1 rounded hover:bg-neutral-200 transition-colors text-neutral-400">
      {ok ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
    </button>
  )
}

function DeviationItem({ dev, index }) {
  const [open, setOpen] = useState(index === 0)
  const rca = dev.root_cause_analysis || {}

  return (
    <div className="border border-neutral-200/60 rounded-xl overflow-hidden bg-white">
      <button onClick={() => setOpen(!open)} className="w-full px-4 py-3 flex items-center gap-3 hover:bg-neutral-50 transition-colors text-left">
        {open ? <ChevronDown className="w-4 h-4 text-neutral-400" /> : <ChevronRight className="w-4 h-4 text-neutral-400" />}
        <span className="text-[13px] font-medium text-neutral-700 flex-1">{dev.id || `DEV-${index + 1}`}: {dev.description?.slice(0, 80)}</span>
        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
          dev.risk_score?.rpn > 15 ? 'bg-red-50 text-red-700' : dev.risk_score?.rpn > 8 ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'
        }`}>RPN {dev.risk_score?.rpn || '—'}</span>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-4 border-t border-neutral-100">
          {/* Root Cause */}
          <div className="mt-3">
            <p className="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-2">5-Why Root Cause</p>
            <div className="space-y-1">
              {['why_1', 'why_2', 'why_3', 'why_4', 'why_5'].map((k, i) => rca[k] && (
                <div key={k} className="flex gap-2 text-[12px]">
                  <span className="text-neutral-400 font-medium w-6">W{i + 1}</span>
                  <span className="text-neutral-600">{rca[k]}</span>
                </div>
              ))}
              {rca.root_cause && (
                <div className="mt-2 p-2 rounded-lg bg-red-50 text-[12px] text-red-700 font-medium">Root cause: {rca.root_cause}</div>
              )}
            </div>
          </div>

          {/* Impact */}
          {dev.impact_assessment && (
            <div>
              <p className="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-2">Impact Assessment</p>
              <div className="grid grid-cols-3 gap-2">
                {Object.entries(dev.impact_assessment).map(([k, v]) => (
                  <div key={k} className="p-2 rounded-lg bg-neutral-50">
                    <p className="text-[10px] text-neutral-400 capitalize">{k.replace('_', ' ')}</p>
                    <p className="text-[11px] text-neutral-700 mt-0.5">{v}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* CAPA */}
          {dev.capa?.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-2">CAPA Actions</p>
              <div className="space-y-1.5">
                {dev.capa.map((c, i) => (
                  <div key={i} className="flex items-start gap-2 p-2 rounded-lg bg-neutral-50">
                    <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded mt-0.5 ${c.type === 'corrective' ? 'bg-blue-50 text-blue-700' : 'bg-purple-50 text-purple-700'}`}>{c.type?.slice(0, 4)}</span>
                    <div className="flex-1">
                      <p className="text-[12px] text-neutral-700">{c.action}</p>
                      <p className="text-[10px] text-neutral-400 mt-0.5">{c.responsible} &middot; {c.deadline}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Regulatory refs */}
          {dev.regulatory_refs?.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-1">Regulatory References</p>
              <div className="flex flex-wrap gap-1">
                {dev.regulatory_refs.map((r, i) => (
                  <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-neutral-100 text-neutral-600">{r}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function DeviationReport({ extraction, validation, compliance, filename }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const run = async () => {
    setLoading(true); setError(null)
    const fd = new FormData()
    fd.append('extraction_data', JSON.stringify(extraction))
    fd.append('validation_data', JSON.stringify(validation || {}))
    fd.append('compliance_data', JSON.stringify(compliance || {}))
    fd.append('filename', filename || '')
    try {
      const r = await fetch('/api/deviation-report', { method: 'POST', body: fd })
      const d = await r.json()
      if (d.error) setError(d.error); else setData(d.result)
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  if (!data && !loading) return (
    <div className="glass rounded-2xl p-6 text-center">
      <FileWarning className="w-8 h-8 text-neutral-300 mx-auto mb-3" />
      <h4 className="text-[15px] font-medium text-neutral-700 tracking-[-0.3px]">Deviation Report Generator</h4>
      <p className="text-[12px] text-neutral-400 mt-1 mb-4 max-w-sm mx-auto tracking-[-0.2px]">
        Generate an FDA 483-ready deviation report with root cause analysis and CAPA actions.
      </p>
      <button onClick={run} className="px-5 py-2 rounded-full bg-neutral-900 text-white text-[13px] font-medium hover:bg-neutral-800 transition-colors">
        Generate Report
      </button>
      {error && <p className="text-[12px] text-red-600 mt-3">{error}</p>}
    </div>
  )

  if (loading) return (
    <div className="glass rounded-2xl p-8 text-center">
      <Loader2 className="w-6 h-6 animate-spin text-neutral-400 mx-auto mb-2" />
      <p className="text-[13px] text-neutral-500">Generating deviation report...</p>
    </div>
  )

  const devs = data?.deviations || []
  const riskStyle = { low: 'text-emerald-700 bg-emerald-50', medium: 'text-amber-700 bg-amber-50', high: 'text-orange-700 bg-orange-50', critical: 'text-red-700 bg-red-50' }

  return (
    <div className="glass rounded-2xl overflow-hidden">
      <div className="px-4 py-3 border-b border-black/[0.04] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileWarning className="w-4 h-4 text-neutral-400" />
          <span className="text-[13px] font-medium text-neutral-700 tracking-[-0.2px]">
            Deviation Report {data?.report_id || ''}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${riskStyle[data?.overall_risk] || riskStyle.medium}`}>
            {data?.overall_risk || 'medium'}
          </span>
          <CopyBtn text={JSON.stringify(data, null, 2)} />
        </div>
      </div>
      <div className="p-4 space-y-3">
        {data?.batch_info && (
          <div className="flex gap-4 p-3 rounded-lg bg-neutral-50 text-[12px] text-neutral-600">
            <span>Product: <strong>{data.batch_info.product}</strong></span>
            <span>Batch: <strong>{data.batch_info.batch_number}</strong></span>
            <span>Date: <strong>{data.batch_info.date || data.report_date}</strong></span>
          </div>
        )}
        {devs.length === 0 ? (
          <p className="text-[13px] text-emerald-600 font-medium text-center py-4">No deviations to report</p>
        ) : devs.map((d, i) => <DeviationItem key={i} dev={d} index={i} />)}
      </div>
    </div>
  )
}
