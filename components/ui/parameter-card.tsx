import { AlertCircle, CheckCircle2, AlertTriangle } from 'lucide-react'

type ParameterStatus = 'normal' | 'slightly_low' | 'slightly_high' | 'severely_low' | 'severely_high' | 'unknown'

interface ParameterCardProps {
  name: string
  value: string
  status: ParameterStatus
  normal_range?: string
  impact?: string
  suggestion?: string
}

const statusConfig = {
  normal: {
    color: 'text-[#236b52]',
    bgColor: 'bg-[#e8f5e9]',
    borderColor: 'border-[#236b52]',
    icon: CheckCircle2,
    label: 'Normal'
  },
  slightly_low: {
    color: 'text-[#f57c00]',
    bgColor: 'bg-[#fff3e0]',
    borderColor: 'border-[#f57c00]',
    icon: AlertTriangle,
    label: 'Slightly Low'
  },
  slightly_high: {
    color: 'text-[#f57c00]',
    bgColor: 'bg-[#fff3e0]',
    borderColor: 'border-[#f57c00]',
    icon: AlertTriangle,
    label: 'Slightly High'
  },
  severely_low: {
    color: 'text-[#e44f2b]',
    bgColor: 'bg-[#ffebee]',
    borderColor: 'border-[#e44f2b]',
    icon: AlertCircle,
    label: 'Severely Low'
  },
  severely_high: {
    color: 'text-[#e44f2b]',
    bgColor: 'bg-[#ffebee]',
    borderColor: 'border-[#e44f2b]',
    icon: AlertCircle,
    label: 'Severely High'
  },
  unknown: {
    color: 'text-[#8f8b83]',
    bgColor: 'bg-[#f5f5f5]',
    borderColor: 'border-[#8f8b83]',
    icon: AlertCircle,
    label: 'Unknown'
  }
}

export function ParameterCard({
  name,
  value,
  status,
  normal_range,
  impact,
  suggestion
}: ParameterCardProps) {
  const config = statusConfig[status] || statusConfig.unknown
  const Icon = config.icon

  return (
    <div className={`border-2 ${config.borderColor} ${config.bgColor} p-4 shadow-[3px_3px_0_#141414]`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon className={`size-5 ${config.color}`} />
          <h4 className="font-black text-sm uppercase">{name}</h4>
        </div>
        <span className={`text-xs font-black px-2 py-1 border-2 ${config.borderColor} ${config.color} bg-white`}>
          {config.label}
        </span>
      </div>

      <div className="mb-2">
        <p className={`text-2xl font-black ${config.color}`}>{value}</p>
        {normal_range && (
          <p className="text-xs font-semibold text-[#48453e]">
            Normal: {normal_range}
          </p>
        )}
      </div>

      {impact && (
        <div className="mb-2">
          <p className="text-xs font-bold text-[#141414]">Impact:</p>
          <p className="text-sm font-semibold text-[#48453e]">{impact}</p>
        </div>
      )}

      {suggestion && (
        <div className="mt-3 pt-3 border-t-2 border-[#141414]/20">
          <p className="text-xs font-bold text-[#141414]">Suggestion:</p>
          <p className="text-sm font-semibold text-[#48453e]">{suggestion}</p>
        </div>
      )}
    </div>
  )
}
