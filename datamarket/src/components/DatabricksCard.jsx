import React from 'react'
import { cn } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { TrendingUp, TrendingDown } from 'lucide-react'

export function DatabricksCard({ 
  title, 
  description, 
  value, 
  trend, 
  icon: Icon,
  className = "",
  variant = 'default',
  ...props 
}) {
  const cardVariants = {
    default: 'border-border',
    accent: 'border-databricks-blue bg-gradient-to-br from-blue-50 to-transparent',
    success: 'border-databricks-emerald bg-gradient-to-br from-emerald-50 to-transparent',
    warning: 'border-databricks-amber bg-gradient-to-br from-amber-50 to-transparent',
    info: 'border-databricks-cyan bg-gradient-to-br from-cyan-50 to-transparent'
  }

  return (
    <Card className={cn(
      "transition-all duration-200 hover:shadow-lg hover:scale-[1.02]",
      cardVariants[variant],
      className
    )} {...props}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        {Icon && (
          <div className={cn(
            "h-8 w-8 rounded-databricks flex items-center justify-center",
            variant === 'accent' ? 'bg-databricks-blue' :
            variant === 'success' ? 'bg-databricks-emerald' :
            variant === 'warning' ? 'bg-databricks-amber' :
            variant === 'info' ? 'bg-databricks-cyan' :
            'bg-databricks-blue'
          )}>
            <Icon className="h-4 w-4 text-white" />
          </div>
        )}
      </CardHeader>
      <CardContent>
        <div className="text-xl sm:text-2xl font-bold text-databricks-navy mb-2">
          {value}
        </div>
        {description && (
          <p className="text-sm text-muted-foreground mb-2">
            {description}
          </p>
        )}
        {trend && (
          <div className="flex items-center space-x-2">
            <Badge 
              variant={trend.direction === 'up' ? 'default' : 'destructive'}
              className={cn(
                "text-xs flex items-center space-x-1",
                trend.direction === 'up' 
                  ? 'bg-databricks-emerald/10 text-databricks-emerald border-databricks-emerald/20' 
                  : 'bg-red-50 text-red-600 border-red-200'
              )}
            >
              {trend.direction === 'up' ? (
                <TrendingUp className="h-3 w-3" />
              ) : (
                <TrendingDown className="h-3 w-3" />
              )}
              <span>{trend.value}</span>
            </Badge>
            <span className="text-xs text-muted-foreground">vs last period</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}