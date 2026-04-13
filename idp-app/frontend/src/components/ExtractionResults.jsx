import { useState } from 'react'
import { ChevronDown, ChevronRight, CheckCircle, AlertTriangle, XCircle } from 'lucide-react'

function Confidence({ level }) {
  if (!level) return null
  const dot = { high: 'bg-emerald-500', medium: 'bg-amber-500', low: 'bg-red-500' }
  return (
    <span className="inline-flex items-center gap-1.5 text-[10px] font-medium text-neutral-500 uppercase tracking-wider">
      <span className={`w-1.5 h-1.5 rounded-full ${dot[level] || dot.medium}`} />
      {level}
    </span>
  )
}

function ValIcon({ status }) {
  if (!status) return null
  if (status === 'pass') return <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
  if (status === 'warning') return <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
  return <XCircle className="w-3.5 h-3.5 text-red-500" />
}

function FieldRow({ label, field, vs }) {
  if (!field) return null
  const value = typeof field === 'object' ? field.value : field
  const confidence = typeof field === 'object' ? field.confidence : null
  return (
    <tr className="border-b border-neutral-100/80 hover:bg-neutral-50/50 transition-colors">
      <td className="py-2 px-3 text-[11px] font-medium text-neutral-400 uppercase tracking-wider w-36">{label}</td>
      <td className="py-2 px-3 text-[13px] font-mono text-neutral-800 tracking-[-0.3px]">
        {value != null ? String(value) : <span className="text-neutral-300 italic">null</span>}
      </td>
      <td className="py-2 px-3 w-16"><Confidence level={confidence} /></td>
      <td className="py-2 px-3 w-8"><ValIcon status={vs} /></td>
    </tr>
  )
}

export default function ExtractionResults({ data, validation }) {
  const [showRaw, setShowRaw] = useState(false)
  const [ingOpen, setIngOpen] = useState(true)
  if (!data) return null

  const vr = validation?.validation_results || {}
  const fields = [
    ['Product Name', data.product_name, vr.product_name?.status],
    ['Batch Number', data.batch_number, vr.batch_number?.status],
    ['Mfg Date', data.manufacturing_date, vr.manufacturing_date?.status],
    ['Expiry Date', data.expiry_date, vr.expiry_date?.status],
    ['Operator', data.operator_initials, vr.operator_initials?.status],
    ['Start Time', data.start_timestamp, vr.start_timestamp?.status],
    ['End Time', data.end_timestamp, vr.end_timestamp?.status],
  ]
  const ingredients = data.ingredients || []
  const equipment = data.equipment_ids || []

  return (
    <div className="glass rounded-2xl overflow-hidden">
      <div className="px-4 py-3 border-b border-black/[0.04] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          <span className="text-[13px] font-medium text-neutral-700 tracking-[-0.2px]">Extracted Data</span>
          {validation && (
            <span className="text-[11px] text-neutral-400 ml-1">
              {validation.passed}/{validation.total_fields} passed
            </span>
          )}
        </div>
        <button onClick={() => setShowRaw(!showRaw)} className="text-[11px] font-medium text-neutral-500 hover:text-neutral-800 transition-colors">
          {showRaw ? 'Table' : 'JSON'}
        </button>
      </div>

      {showRaw ? (
        <pre className="p-4 text-[11px] font-mono text-neutral-600 overflow-auto max-h-[500px] bg-neutral-50/50">
          {JSON.stringify(data, null, 2)}
        </pre>
      ) : (
        <div className="overflow-auto max-h-[500px]">
          <table className="w-full">
            <tbody>
              {fields.map(([l, f, vs]) => <FieldRow key={l} label={l} field={f} vs={vs} />)}

              {ingredients.length > 0 && (
                <>
                  <tr className="border-b border-neutral-100 cursor-pointer hover:bg-neutral-50/50" onClick={() => setIngOpen(!ingOpen)}>
                    <td colSpan={4} className="py-2 px-3">
                      <div className="flex items-center gap-1.5 text-[13px] font-medium text-neutral-700 tracking-[-0.2px]">
                        {ingOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                        Ingredients ({ingredients.length})
                      </div>
                    </td>
                  </tr>
                  {ingOpen && ingredients.map((ing, i) => (
                    <tr key={i} className="border-b border-neutral-50 bg-neutral-50/30">
                      <td className="py-2 px-3 pl-6 text-[11px] text-neutral-400">#{i + 1}</td>
                      <td colSpan={2} className="py-2 px-3 text-[12px] font-mono text-neutral-700 space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="text-neutral-400 text-[10px] w-12">Name</span>
                          {typeof ing.ingredient_name === 'object' ? ing.ingredient_name?.value : ing.ingredient_name}
                          {typeof ing.ingredient_name === 'object' && <Confidence level={ing.ingredient_name?.confidence} />}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-neutral-400 text-[10px] w-12">Weight</span>
                          {typeof ing.weight_kg === 'object' ? ing.weight_kg?.value : ing.weight_kg} kg
                          {typeof ing.weight_kg === 'object' && <Confidence level={ing.weight_kg?.confidence} />}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-neutral-400 text-[10px] w-12">Lot #</span>
                          {typeof ing.lot_number === 'object' ? ing.lot_number?.value : ing.lot_number}
                          {typeof ing.lot_number === 'object' && <Confidence level={ing.lot_number?.confidence} />}
                        </div>
                      </td>
                      <td className="py-2 px-3"><ValIcon status={vr[`ingredient_${i+1}`]?.status} /></td>
                    </tr>
                  ))}
                </>
              )}

              {equipment.map((eq, i) => (
                <FieldRow key={`eq-${i}`} label={`Equip ${i+1}`} field={eq} vs={vr[`equipment_${i+1}`]?.status} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
