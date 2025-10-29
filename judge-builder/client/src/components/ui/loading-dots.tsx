import { cn } from "@/lib/utils"

interface LoadingDotsProps {
  className?: string
  size?: "sm" | "md" | "lg"
}

export function LoadingDots({ className, size = "md" }: LoadingDotsProps) {
  const sizeClasses = {
    sm: "w-1 h-1",
    md: "w-2 h-2", 
    lg: "w-3 h-3"
  }

  const containerClasses = {
    sm: "space-x-0.5",
    md: "space-x-1",
    lg: "space-x-1.5"
  }

  return (
    <div className={cn("flex items-center justify-center", containerClasses[size], className)}>
      <div 
        className={cn(
          "bg-current rounded-full animate-pulse",
          sizeClasses[size]
        )}
        style={{
          animationDelay: "0ms",
          animationDuration: "600ms"
        }}
      />
      <div 
        className={cn(
          "bg-current rounded-full animate-pulse",
          sizeClasses[size]
        )}
        style={{
          animationDelay: "200ms",
          animationDuration: "600ms"
        }}
      />
      <div 
        className={cn(
          "bg-current rounded-full animate-pulse",
          sizeClasses[size]
        )}
        style={{
          animationDelay: "400ms",
          animationDuration: "600ms"
        }}
      />
    </div>
  )
}