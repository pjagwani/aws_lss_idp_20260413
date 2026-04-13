import { useState } from 'react'
import { ChevronDown, ChevronRight, CircleDot, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'

function ConfidenceBadge({ level }) {
  if (!level) return null
  const styles = {
    high: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    medium: 'bg-amber-100 text-amber-700 border-amber-200',
    low: 'bg-red-100 text-red-700 border-red-200',
  }
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${styles[level] || styles.medium}`}>
      <CircleDot className="w-2.5 h-2.5" />
      {level}
    </span>
  )
}

function ValidationBadge({ status }) {
  if (!status) return null
  if (status === 'pass') return <CheckCircle className="w-4 h-4 text-emerald-500" />
  if (status === 'warning') return <AlertTriangle className="w-4 h-4 text-amber-500" />
  return <XCircle className="w-4 h-4 text-red-500" />
}

function FieldRow({ label, field, validationStatus }) {
  if (!field) return null
  const value = typeof field === 'object' ? field.value : field
  const confidence = typeof field === 'object' ? field.confidence : null

  return (
    <tr className="border-b border-slate-50 hover:bg-teal-50/50 transition-colors">
      <td className="py-2.5 px-3 text-xs font-medium text-slate-500 uppercase tracking-wider w-40">
        {label}
      </td>
      <td className="py-2.5 px-3 text-sm font-mono text-slate-800">
        {value !== null && value !== undefined ? String(value) : <span className="text-slate-300 italic">null</span>}
      </td>
      <td className="py-2.5 px-3 w-20">
        <ConfidenceBadge level={confidence} />
      </td>
      <td className="py-2.5 px-3 w-10">
        <ValidationBadge status={validationStatus} />
      </td>
    </tr>
  )
}

export default function ExtractionResults({ data, validation }) {
  const [showRaw, setShowRaw] = useState(false)
  const [ingredientsOpen, setIngredientsOpen] = useState(true)

  if (!data) return null

  const vr = validation?.validation_results || {}

  // Extract top-level fields
  const topFields = [
    ['Product Name', data.product_name, vr.product_name?.status],
    ['Batch Number', data.batch_number, vr.batch_number?.status],
    ['Manufacturing Date', data.manufacturing_date, vr.manufacturing_date?.status],
    ['Expiry Date', data.expiry_date, vr.expiry_date?.status],
    ['Operator Initials', data.operator_initials, vr.operator_initials?.status],
    ['Start Time', data.start_timestamp, vr.start_timestamp?.status],
    ['End Time', data.end_timestamp, vr.end_timestamp?.status],
  ]

  const ingredients = data.ingredients || []
  const equipment = data.equipment_ids || []

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500" />
          <span className="text-sm font-semibold text-slate-700">Extracted Data</span>
          {validation && (
            <span className="text-xs text-slate-400">
              {validation.passed}/{validation.total_fields} passed
            </span>
          )}
        </div>
        <button
          onClick={() => setShowRaw(!showRaw)}
          className="text-xs text-teal-600 hover:text-teal-700 font-medium"
        >
          {showRaw ? 'Table View' : 'Raw JSON'}
        </button>
      </div>

      {showRaw ? (
        <pre className="p-4 text-xs font-mono text-slate-700 overflow-auto max-h-[500px] bg-slate-50">
          {JSON.stringify(data, null, 2)}
        </pre>
      ) : (
        <div className="overflow-auto max-h-[500px]">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="text-left text-[10px] font-semibold text-slate-400 uppercase tracking-wider py-2 px-3">Field</th>
                <th className="text-left text-[10px] font-semibold text-slate-400 uppercase tracking-wider py-2 px-3">Value</th>
                <th className="text-left text-[10px] font-semibold text-slate-400 uppercase tracking-wider py-2 px-3 w-20">Conf.</th>
                <th className="w-10 py-2 px-3"></th>
              </tr>
            </thead>
            <tbody>
              {topFields.map(([label, field, vs]) => (
                <FieldRow key={label} label={label} field={field} validationStatus={vs} />
              ))}

              {/* Ingredients section */}
              {ingredients.length > 0 && (
                <>
                  <tr
                    className="border-b border-slate-100 cursor-pointer hover:bg-teal-50/50"
                    onClick={() => setIngredientsOpen(!ingredientsOpen)}
                  >
                    <td colSpan={4} className="py-2.5 px-3">
                      <div className="flex items-center gap-2 text-sm font-semibold text-teal-700">
                        {ingredientsOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                        Ingredients ({ingredients.length})
                      </div>
                    </td>
                  </tr>
                  {ingredientsOpen && ingredients.map((ing, i) => (
                    <tr key={i} className="border-b border-slate-50 bg-teal-50/20">
                      <td className="py-2 px-3 pl-8 text-xs text-slate-500">#{i + 1}</td>
                      <td colSpan={2} className="py-2 px-3 text-sm font-mono text-slate-800">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-slate-400 text-xs w-16">Name:</span>
                            <span>{typeof ing.ingredient_name === 'object' ? ing.ingredient_name?.value : ing.ingredient_name}</span>
                            {typeof ing.ingredient_name === 'object' && <ConfidenceBadge level={ing.ingredient_name?.confidence} />}
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-slate-400 text-xs w-16">Weight:</span>
                            <span>{typeof ing.weight_kg === 'object' ? ing.weight_kg?.value : ing.weight_kg} kg</span>
                            {typeof ing.weight_kg === 'object' && <ConfidenceBadge level={ing.weight_kg?.confidence} />}
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-slate-400 text-xs w-16">Lot #:</span>
                            <span>{typeof ing.lot_number === 'object' ? ing.lot_number?.value : ing.lot_number}</span>
                            {typeof ing.lot_number === 'object' && <ConfidenceBadge level={ing.lot_number?.confidence} />}
                          </div>
                        </div>
                      </td>
                      <td className="py-2 px-3">
                        <ValidationBadge status={vr[`ingredient_${i + 1}`]?.status} />
                      </td>
                    </tr>
                  ))}
                </>
              )}

              {/* Equipment */}
              {equipment.length > 0 && equipment.map((eq, i) => (
                <FieldRow
                  key={`eq-${i}`}
                  label={`Equipment ${i + 1}`}
                  field={eq}
                  validationStatus={vr[`equipment_${i + 1}`]?.status}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
