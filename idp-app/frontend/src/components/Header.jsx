export default function Header() {
  const pills = ['Strands SDK', 'Bedrock', 'AgentCore Memory', 'BDA MCP']

  return (
    <header className="border-b border-black/[0.06]">
      <div className="max-w-[1320px] mx-auto px-6 py-5 flex items-center justify-between">
        {/* Logo + title */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-black flex items-center justify-center">
            <span className="text-white text-sm font-bold">IDP</span>
          </div>
          <div>
            <h1 className="text-[15px] font-semibold tracking-[-0.3px] text-neutral-950 m-0">
              Pharma IDP Pipeline
            </h1>
            <p className="text-[12px] text-neutral-400 tracking-[-0.2px] m-0">
              Intelligent Document Processing
            </p>
          </div>
        </div>

        {/* Tech pills */}
        <div className="hidden md:flex items-center gap-2">
          {pills.map(label => (
            <span
              key={label}
              className="px-3 py-1 rounded-full text-[11px] font-medium tracking-[-0.2px]
                         text-neutral-500 bg-neutral-100 border border-neutral-200/60"
            >
              {label}
            </span>
          ))}
          <span className="px-3 py-1 rounded-full text-[11px] font-semibold tracking-[-0.2px]
                           text-amber-700 bg-amber-50 border border-amber-200/60">
            ALCOA+
          </span>
        </div>
      </div>

      {/* Architecture flow */}
      <div className="border-t border-black/[0.04] bg-white/50">
        <div className="max-w-[1320px] mx-auto px-6 py-2 flex items-center justify-center gap-3 text-[11px] text-neutral-400 tracking-[-0.2px]">
          <span>Upload</span>
          <span className="text-neutral-300">&rarr;</span>
          <span className="text-neutral-600 font-medium">Extraction</span>
          <span className="text-neutral-300">&rarr;</span>
          <span className="text-neutral-600 font-medium">Validation</span>
          <span className="text-neutral-300">&rarr;</span>
          <span className="text-neutral-600 font-medium">Compliance</span>
          <span className="text-neutral-300">&rarr;</span>
          <span>Output</span>
        </div>
      </div>
    </header>
  )
}
