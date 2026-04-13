import { FileText } from 'lucide-react'

export default function DocumentViewer({ document }) {
  if (!document) return null

  return (
    <div className="glass rounded-2xl overflow-hidden">
      <div className="px-4 py-3 border-b border-black/[0.04] flex items-center gap-2">
        <FileText className="w-4 h-4 text-neutral-400" />
        <span className="text-[13px] font-medium text-neutral-700 tracking-[-0.2px]">{document.name}</span>
        <span className="text-[11px] text-neutral-400 ml-auto">Source</span>
      </div>
      <div className="h-[600px] bg-neutral-50">
        <iframe
          src={`${document.url}#toolbar=0&navpanes=0`}
          className="w-full h-full border-0"
          title="Document preview"
        />
      </div>
    </div>
  )
}
