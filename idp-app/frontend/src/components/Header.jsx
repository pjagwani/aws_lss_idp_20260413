import { FlaskConical, Shield, Cpu, Database, Cloud } from 'lucide-react'

const techStack = [
  { label: 'Strands SDK', icon: Cpu },
  { label: 'BDA MCP', icon: Database },
  { label: 'AgentCore', icon: Cloud },
  { label: 'Bedrock', icon: Cloud },
]

export default function Header() {
  return (
    <header className="relative overflow-hidden">
      {/* Gradient banner */}
      <div className="bg-gradient-to-r from-teal-800 via-teal-700 to-emerald-800 text-white">
        {/* Decorative circles */}
        <div className="absolute top-[-60px] right-[-40px] w-[300px] h-[300px] rounded-full bg-white/5" />
        <div className="absolute bottom-[-80px] left-[10%] w-[200px] h-[200px] rounded-full bg-white/3" />

        <div className="relative max-w-[1600px] mx-auto px-6 py-6">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-white/15 backdrop-blur flex items-center justify-center">
                <FlaskConical className="w-7 h-7 text-emerald-200" />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight m-0">
                  IDP Agent Pipeline
                </h1>
                <p className="text-teal-200 text-sm mt-0.5">
                  Pharmaceutical Manufacturing Document Processing
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* Tech pills */}
              <div className="hidden md:flex items-center gap-2">
                {techStack.map(({ label, icon: Icon }) => (
                  <span
                    key={label}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full
                               bg-white/10 backdrop-blur border border-white/10
                               text-xs font-medium text-teal-100"
                  >
                    <Icon className="w-3.5 h-3.5" />
                    {label}
                  </span>
                ))}
              </div>

              {/* ALCOA+ badge */}
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                              bg-amber-400/20 border border-amber-400/30">
                <Shield className="w-4 h-4 text-amber-300" />
                <span className="text-xs font-semibold text-amber-200">ALCOA+</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Architecture bar */}
      <div className="bg-white/80 backdrop-blur border-b border-teal-100">
        <div className="max-w-[1600px] mx-auto px-6 py-2.5 flex items-center justify-center gap-2 text-xs text-slate-500">
          <span className="font-medium text-teal-700">Architecture:</span>
          <span>Document Upload</span>
          <span className="text-teal-400">&rarr;</span>
          <span className="text-teal-700 font-medium">Extraction Agent</span>
          <span className="text-teal-400">&rarr;</span>
          <span className="text-teal-700 font-medium">Validation Agent</span>
          <span className="text-teal-400">&rarr;</span>
          <span className="text-teal-700 font-medium">Compliance Agent</span>
          <span className="text-teal-400">&rarr;</span>
          <span>Structured Output</span>
        </div>
      </div>
    </header>
  )
}
