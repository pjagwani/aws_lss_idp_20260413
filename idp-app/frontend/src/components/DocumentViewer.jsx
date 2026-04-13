import { FileText } from 'lucide-react'

export default function DocumentViewer({ document }) {
  if (!document) return null

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      {/* Title bar */}
      <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2">
        <FileText className="w-4 h-4 text-teal-600" />
        <span className="text-sm font-semibold text-slate-700">{document.name}</span>
        <span className="text-xs text-slate-400 ml-auto">Source Document</span>
      </div>

      {/* PDF embed */}
      <div className="h-[600px] bg-slate-50">
        <iframe
          src={`${document.url}#toolbar=0&navpanes=0`}
          className="w-full h-full border-0"
          title="Document preview"
        />
      </div>
    </div>
  )
}
