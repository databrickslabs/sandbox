import React from 'react'
import { cn } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { TrendingUp, BarChart3, LineChart as LineChartIcon } from 'lucide-react'

const DATABRICKS_COLORS = ['#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#06b6d4', '#ec4899']

export function DatabricksChart({ 
  type = 'line',
  data = [],
  xKey,
  yKeys = [],
  title,
  subtitle,
  className = "",
  height = 400,
  showLegend = true,
  showGrid = true,
  ...props 
}) {
  const ChartComponent = {
    line: LineChart,
    area: AreaChart,
    bar: BarChart
  }[type]

  const getChartIcon = () => {
    switch (type) {
      case 'bar': return BarChart3
      case 'area': return TrendingUp  
      default: return LineChartIcon
    }
  }

  const ChartIcon = getChartIcon()

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <Card className="shadow-lg border-border">
          <CardContent className="p-3">
            <p className="text-sm font-medium text-foreground mb-2">{label}</p>
            <div className="space-y-1">
              {payload.map((entry, index) => (
                <div key={index} className="flex items-center justify-between space-x-3">
                  <div className="flex items-center space-x-2">
                    <div 
                      className="w-3 h-3 rounded-full" 
                      style={ { backgroundColor: entry.color } }
                    />
                    <span className="text-sm text-muted-foreground">{entry.name}</span>
                  </div>
                  <span className="text-sm font-medium" style={ { color: entry.color } }>
                    {entry.value.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )
    }
    return null
  }

  return (
    <Card className={cn("transition-all duration-200 hover:shadow-lg", className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="space-y-1">
          <CardTitle className="text-base font-semibold text-foreground flex items-center space-x-2">
            <ChartIcon className="h-4 w-4 text-databricks-blue" />
            <span>{title}</span>
          </CardTitle>
          {subtitle && (
            <p className="text-sm text-muted-foreground">{subtitle}</p>
          )}
        </div>
        <Badge variant="outline" className="text-xs">
          {data.length} {data.length === 1 ? 'point' : 'points'}
        </Badge>
      </CardHeader>
      <CardContent>
              <ResponsiveContainer 
        width="100%" 
        height={height}
        minHeight={200}
      >
        <ChartComponent data={data} margin={ { top: 5, right: 10, left: 10, bottom: 5 } } {...props}>
            {showGrid && (
              <CartesianGrid 
                strokeDasharray="3 3" 
                stroke="hsl(var(--border))" 
                opacity={0.3}
              />
            )}
                      <XAxis 
            dataKey={xKey} 
            stroke="hsl(var(--muted-foreground))"
            fontSize={10}
            fontFamily="Inter"
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
            minTickGap={10}
          />
          <YAxis 
            stroke="hsl(var(--muted-foreground))"
            fontSize={10}
            fontFamily="Inter"
            tickLine={false}
            axisLine={false}
            tickFormatter={(value) => {
              if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`
              if (value >= 1000) return `${(value / 1000).toFixed(0)}K`
              return value.toLocaleString()
            }}
            width={60}
          />
            <Tooltip content={<CustomTooltip />} />
            {showLegend && <Legend />}
            {yKeys.map((key, index) => {
              const color = DATABRICKS_COLORS[index % DATABRICKS_COLORS.length]
              const commonProps = {
                key,
                dataKey: key,
                stroke: color,
                strokeWidth: 2,
                name: key.charAt(0).toUpperCase() + key.slice(1)
              }

              if (type === 'area') {
                return <Area {...commonProps} fill={color} fillOpacity={0.1} />
              } else if (type === 'bar') {
                return <Bar {...commonProps} fill={color} radius={[4, 4, 0, 0]} />
              } else {
                return <Line {...commonProps} dot={ { fill: color, strokeWidth: 2, r: 4 } } />
              }
            })}
          </ChartComponent>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}