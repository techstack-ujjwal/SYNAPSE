import { ArrowUp, ArrowDown, Minus, TrendingUp, TrendingDown, Activity } from 'lucide-react'

interface ComparisonItem {
  improved: string[]
  deteriorated: string[]
  unchanged: string[]
  new_abnormalities: string[]
  resolved_abnormalities: string[]
}

interface ReportComparisonProps {
  comparison: ComparisonItem
  summary: string
  pastReportName: string
  presentReportName: string
}

export function ReportComparison({
  comparison,
  summary,
  pastReportName,
  presentReportName
}: ReportComparisonProps) {
  return (
    <div className="border-2 border-[#141414] bg-white p-6 shadow-[6px_6px_0_#141414]">
      {/* Header */}
      <div className="flex items-center justify-between border-b-2 border-[#141414] pb-4 mb-4">
        <div className="flex items-center gap-2">
          <Activity className="size-5 text-[#e44f2b]" />
          <h3 className="text-2xl font-black">Report Comparison</h3>
        </div>
        <div className="text-right text-sm">
          <p className="font-semibold text-[#8f8b83]">Past:</p>
          <p className="font-black">{pastReportName}</p>
          <p className="font-semibold text-[#8f8b83] mt-2">Present:</p>
          <p className="font-black">{presentReportName}</p>
        </div>
      </div>

      {/* Summary */}
      {summary && (
        <div className="mb-6 bg-[#e8f5e9] border-2 border-[#236b52] p-4">
          <p className="text-sm font-black uppercase text-[#236b52] mb-2">Overall Summary</p>
          <p className="font-semibold text-[#141414]">{summary}</p>
        </div>
      )}

      {/* Comparison Sections */}
      <div className="space-y-4">
        {/* Improved */}
        {comparison.improved && comparison.improved.length > 0 && (
          <div className="border-2 border-[#236b52] bg-[#e8f5e9] p-4">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="size-5 text-[#236b52]" />
              <h4 className="font-black text-lg text-[#236b52]">Improved Parameters</h4>
            </div>
            <ul className="space-y-2">
              {comparison.improved.map((item, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <ArrowUp className="size-4 text-[#236b52] mt-0.5 shrink-0" />
                  <span className="font-semibold text-[#141414]">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Deteriorated */}
        {comparison.deteriorated && comparison.deteriorated.length > 0 && (
          <div className="border-2 border-[#e44f2b] bg-[#ffebee] p-4">
            <div className="flex items-center gap-2 mb-3">
              <TrendingDown className="size-5 text-[#e44f2b]" />
              <h4 className="font-black text-lg text-[#e44f2b]">Deteriorated Parameters</h4>
            </div>
            <ul className="space-y-2">
              {comparison.deteriorated.map((item, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <ArrowDown className="size-4 text-[#e44f2b] mt-0.5 shrink-0" />
                  <span className="font-semibold text-[#141414]">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* New Abnormalities */}
        {comparison.new_abnormalities && comparison.new_abnormalities.length > 0 && (
          <div className="border-2 border-[#f57c00] bg-[#fff3e0] p-4">
            <div className="flex items-center gap-2 mb-3">
              <Activity className="size-5 text-[#f57c00]" />
              <h4 className="font-black text-lg text-[#f57c00]">New Abnormalities</h4>
            </div>
            <ul className="space-y-2">
              {comparison.new_abnormalities.map((item, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-[#f57c00] font-black">⚠</span>
                  <span className="font-semibold text-[#141414]">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Resolved Abnormalities */}
        {comparison.resolved_abnormalities && comparison.resolved_abnormalities.length > 0 && (
          <div className="border-2 border-[#236b52] bg-[#e8f5e9] p-4">
            <div className="flex items-center gap-2 mb-3">
              <Activity className="size-5 text-[#236b52]" />
              <h4 className="font-black text-lg text-[#236b52]">Resolved Abnormalities</h4>
            </div>
            <ul className="space-y-2">
              {comparison.resolved_abnormalities.map((item, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-[#236b52] font-black">✓</span>
                  <span className="font-semibold text-[#141414]">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Unchanged */}
        {comparison.unchanged && comparison.unchanged.length > 0 && (
          <div className="border-2 border-[#8f8b83] bg-[#f5f5f5] p-4">
            <div className="flex items-center gap-2 mb-3">
              <Minus className="size-5 text-[#8f8b83]" />
              <h4 className="font-black text-lg text-[#8f8b83]">Unchanged Parameters</h4>
            </div>
            <ul className="space-y-2">
              {comparison.unchanged.map((item, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-[#8f8b83]">→</span>
                  <span className="font-semibold text-[#141414]">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
