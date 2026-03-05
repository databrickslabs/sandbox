// Simple toast implementation for development
import { useState, useCallback } from "react"

export interface Toast {
  title: string
  description?: string
  variant?: "default" | "destructive" | "success"
}

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([])

  const toast = useCallback((newToast: Toast) => {
    setToasts(prev => [...prev, newToast])
    
    // Auto remove after 5 seconds
    setTimeout(() => {
      setToasts(prev => prev.slice(1))
    }, 5000)
  }, [])

  return { toast, toasts }
}