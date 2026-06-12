import { AlertTriangle } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

export function AuditAlert({ telemetry }) {
  const errorType    = telemetry?.last_error_type
  const errorDetails = telemetry?.last_error_details

  if (!errorType || errorType === 'None' || !errorDetails) return null

  return (
    <Alert variant="destructive" className="bg-red-950/40 border-red-900/50 text-red-200">
      <AlertTriangle className="h-4 w-4 stroke-red-500" />
      <AlertTitle className="text-red-400 font-bold tracking-wide uppercase text-xs mb-2">Audit Alert: {errorType}</AlertTitle>
      <AlertDescription className="font-mono text-[0.7rem] leading-relaxed max-h-36 overflow-y-auto pr-2 opacity-90 whitespace-pre-wrap">
        {errorDetails}
      </AlertDescription>
    </Alert>
  )
}
