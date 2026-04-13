import { useState, useEffect } from 'react'
import { GitCompare, Loader2, CheckCircle, XCircle, AlertTriangle } from 'lucide-react'

export default function MultiDocReconciliation() {
  const [samples, setSamples] = useState([])
  const [selected, setSelected] = useState([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/samples').then(r => r.json()).then(d => setSamples(d.samples || []))
  }, [])

  const toggle = (name) => {
    setSelected(prev => prev.includes(name) ? prev.filter(n => n !== name) : [...prev, name])
  }

  const run = async () => {
    if (selected.length < 2) return
    setLoading(true); setError(null); setResult(null)
    const fd = new FormData()
    fd.append('sample_names', selected.join(','))
    try {
      const r = await fetch('/api/reconcile', { method: 'POST', body: fd })
      const d = await r.json()
      if (d.error) setError(d.error); else setResult(d)
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  const recon = result?.reconciliation
  const statusIcon = { match: <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />, mismatch: <XCircle className="w-3.5 h-3.5 text-red-500" />, partial: <AlertTriangle className="w-3.5 h-3.5 text-amber-500" /> }
  const statusStyle = { reconciled: 'text-emerald-700 bg-emerald-50', discrepancies_found: 'text-red-700 bg-red-50', insufficient_data: 'text-amber-700 bg-amber-50' }

  return (
    <div className="max-w-[1320px] mx-auto mt-8 space-y-6">
      {/* Document selector */}
      <div className="glass rounded-2xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <GitCompare className="w-5 h-5 text-neutral-400" />
          <h3 className="text-[15px] font-medium text-neutral-700 tracking-[-0.3px]">Multi-Document Reconciliation</h3>
        </div>
        <p className="text-[12px] text-neutral-400 mb-4 tracking-[-0.2px]">
          Select 2+ documents to cross-reference batch numbers, ingredients, timestamps, and operators.
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 mb-4">
          {samples.map(s => (
            <button key={s.name} onClick={() => toggle(s.name)}
              className={`p-3 rounded-xl border text-left transition-all text-[12px] ${
                selected.includes(s.name)
                  ? 'border-neutral-900 bg-neutral-900 text-white'
                  : 'border-neutral-200/60 bg-white text-neutral-700 hover:border-neutral-300'
              }`}>
              <p className="font-medium truncate">{s.name}</p>
              <p className={`text-[10px] mt-0.5 ${selected.includes(s.name) ? 'text-neutral-300' : 'text-neutral-400'}`}>
                {(s.size / 1024).toFixed(1)} KB
              </p>
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <button onClick={run} disabled={selected.length < 2 || loading}
            className="px-5 py-2 rounded-full bg-neutral-900 text-white text-[13px] font-medium hover:bg-neutral-800 transition-colors disabled:opacity-30">
            {loading ? <Loader2 className="w-4 h-4 animate-spin inline mr-1" /> : null}
            Reconcile {selected.length} Documents
          </button>
          <span className="text-[11px] text-neutral-400">{selected.length < 2 ? 'Select at least 2' : `${selected.length} selected`}</span>
        </div>
        {error && <p className="text-[12px] text-red-600 mt-3">{error}</p>}
      </div>

      {/* Results */}
      {recon && (
        <div className="glass rounded-2xl overflow-hidden">
          <div className="px-4 py-3 border-b border-black/[0.04] flex items-center justify-between">
            <span className="text-[13px] font-medium text-neutral-700">Reconciliation Results</span>
            <div className="flex items-center gap-2">
              <span className="text-[12px] font-bold text-neutral-700">{recon.reconciliation_score}/100</span>
              <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${statusStyle[recon.overall_status] || statusStyle.discrepancies_found}`}>
                {recon.overall_status?.replace('_', ' ')}
              </span>
            </div>
          </div>

          <div className="p-4 space-y-4">
            {recon.summary && <p className="text-[13px] text-neutral-600 tracking-[-0.2px]">{recon.summary}</p>}

            {/* Matches */}
            {recon.matches?.length > 0 && (
              <div>
                <p className="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-2">Field Comparison</p>
                <div className="space-y-1">
                  {recon.matches.map((m, i) => (
                    <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg bg-neutral-50">
                      {statusIcon[m.status] || statusIcon.partial}
                      <span className="text-[12px] font-medium text-neutral-700 w-32">{m.field}</span>
                      <div className="flex-1 text-[11px] text-neutral-500">
                        {m.values && Object.entries(m.values).map(([doc, val], j) => (
                          <span key={doc}>
                            {j > 0 && ' vs '}
                            <strong className={m.status === 'mismatch' ? 'text-red-600' : 'text-neutral-700'}>{String(val)}</strong>
                          </span>
                        ))}
                      </div>
                      {m.notes && <span className="text-[10px] text-neutral-400">{m.notes}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Discrepancies */}
            {recon.discrepancies?.length > 0 && (
              <div>
                <p className="text-[10px] font-semibold text-red-400 uppercase tracking-widest mb-2">Discrepancies</p>
                <div className="space-y-1.5">
                  {recon.discrepancies.map((d, i) => (
                    <div key={i} className="p-3 rounded-lg border border-red-200/60 bg-red-50/50">
                      <div className="flex items-center gap-2 mb-1">
                        <XCircle className="w-3.5 h-3.5 text-red-500" />
                        <span className="text-[12px] font-medium text-red-700">{d.field}</span>
                        <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${
                          d.severity === 'critical' ? 'bg-red-100 text-red-700' : d.severity === 'major' ? 'bg-orange-100 text-orange-700' : 'bg-amber-100 text-amber-700'
                        }`}>{d.severity}</span>
                      </div>
                      <p className="text-[11px] text-red-600">{d.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
