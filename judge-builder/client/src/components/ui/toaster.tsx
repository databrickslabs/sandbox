import { useToast } from '@/contexts/ToastContext'

export function Toaster() {
  const { toasts } = useToast()

  if (!toasts || toasts.length === 0) {
    return null
  }

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map((toast, index) => (
        <div
          key={index}
          className={`
            rounded-lg border px-4 py-3 shadow-lg transition-all duration-300 ease-in-out
            ${
              toast.variant === 'destructive'
                ? 'border-red-500 bg-red-50 text-red-900'
                : toast.variant === 'success'
                ? 'border-green-500 bg-green-50 text-green-900'
                : 'border-gray-300 bg-white text-gray-900'
            }
          `}
          style={{ minWidth: '300px' }}
        >
          <div className="font-medium">{toast.title}</div>
          {toast.description && (
            <div className="mt-1 text-sm opacity-90">{toast.description}</div>
          )}
        </div>
      ))}
    </div>
  )
}