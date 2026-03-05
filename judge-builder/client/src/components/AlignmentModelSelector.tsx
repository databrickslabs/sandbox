import { useState, useEffect } from "react"
import { Check, ChevronsUpDown, Info } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { Label } from "@/components/ui/label"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { ServingEndpointsService } from "@/fastapi_client"
import type { AlignmentModelConfig } from "@/fastapi_client"

interface ServingEndpoint {
  name: string
  state: any
  creation_timestamp?: number
}

interface AlignmentModelSelectorProps {
  value?: AlignmentModelConfig | null
  onChange: (config: AlignmentModelConfig | null) => void
  className?: string
  showLabel?: boolean
  showTooltip?: boolean
}

export function AlignmentModelSelector({ value, onChange, className, showLabel = true, showTooltip = false }: AlignmentModelSelectorProps) {
  const [endpoints, setEndpoints] = useState<ServingEndpoint[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedEndpoint, setSelectedEndpoint] = useState<string | null>(
    value?.serving_endpoint?.endpoint_name || null
  )

  useEffect(() => {
    loadEndpoints()
  }, [])

  const loadEndpoints = async () => {
    try {
      setLoading(true)
      const response = await ServingEndpointsService.listServingEndpointsApiServingEndpointsGet()
      setEndpoints(response || [])
    } catch (error) {
      console.error("Failed to load serving endpoints:", error)
      setEndpoints([])
    } finally {
      setLoading(false)
    }
  }

  const handleSelect = (endpointName: string | null) => {
    setSelectedEndpoint(endpointName)
    setOpen(false)
    setSearchQuery("")

    if (endpointName === null) {
      onChange(null)
    } else {
      onChange({
        model_type: "serving_endpoint",
        serving_endpoint: {
          endpoint_name: endpointName
        }
      })
    }
  }

  // Filter endpoints based on search query
  const filteredEndpoints = endpoints.filter(endpoint => {
    if (!searchQuery.trim()) return true
    const query = searchQuery.toLowerCase()
    return endpoint.name.toLowerCase().includes(query)
  })

  // Handle manual entry when user types an endpoint name that doesn't exist
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (searchQuery.trim() && !filteredEndpoints.some(e => e.name === searchQuery.trim())) {
        // User is typing a manual endpoint name
      }
    }, 300)

    return () => clearTimeout(timeoutId)
  }, [searchQuery, filteredEndpoints])

  return (
    <TooltipProvider>
      <div className={cn(showLabel ? "space-y-2" : "", className)}>
        {showLabel && (
          <div className="flex items-center gap-1">
            <Label className="text-sm font-medium">
              Alignment Model <span className="text-muted-foreground font-normal">(optional)</span>
            </Label>
            {showTooltip && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <button type="button" className="inline-flex items-center">
                    <Info className="h-4 w-4 text-muted-foreground" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>
                    The "teacher" model that optimizes the judge to align with human feedback. The judge itself uses the default Agent Evaluation model described <a href="https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/concepts/judges" target="_blank" rel="noopener noreferrer" className="underline text-blue-600">here</a>
                  </p>
                </TooltipContent>
              </Tooltip>
            )}
          </div>
        )}

        <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-full justify-between"
          >
            {loading ? (
              "Loading endpoints..."
            ) : selectedEndpoint ? (
              selectedEndpoint
            ) : (
              "Default"
            )}
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[400px] p-0">
          <div className="flex flex-col">
            <div className="border-b px-3 py-2">
              <input
                type="text"
                placeholder="Search endpoints or type endpoint name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-2 py-1 text-sm border-0 outline-none bg-transparent"
              />
            </div>
            <div className="max-h-60 overflow-auto">
              {/* Default option */}
              <div
                className="flex items-center p-2 text-sm cursor-pointer hover:bg-accent hover:text-accent-foreground"
                onClick={() => handleSelect(null)}
              >
                <Check
                  className={cn(
                    "mr-2 h-4 w-4",
                    selectedEndpoint === null ? "opacity-100" : "opacity-0"
                  )}
                />
                <div className="flex-1">
                  <div className="font-medium">Default</div>
                  <div className="text-xs text-gray-500">Use a Databricks-managed endpoint</div>
                </div>
              </div>

              {loading ? (
                <div className="p-3 text-sm text-center text-muted-foreground">Loading endpoints...</div>
              ) : filteredEndpoints.length === 0 && !searchQuery.trim() ? (
                <div className="p-3 text-sm text-center text-muted-foreground">No serving endpoints found</div>
              ) : filteredEndpoints.length === 0 && searchQuery.trim() ? (
                <div
                  className="flex items-center p-2 text-sm cursor-pointer hover:bg-accent hover:text-accent-foreground border-t"
                  onClick={() => handleSelect(searchQuery.trim())}
                >
                  <div className="flex-1">
                    <div className="font-medium text-blue-600">Use "{searchQuery.trim()}"</div>
                    <div className="text-xs text-gray-500">Enter endpoint name manually</div>
                  </div>
                </div>
              ) : (
                <>
                  {filteredEndpoints.map((endpoint) => (
                    <div
                      key={endpoint.name}
                      className="flex items-center p-2 text-sm cursor-pointer hover:bg-accent hover:text-accent-foreground"
                      onClick={() => handleSelect(endpoint.name)}
                    >
                      <Check
                        className={cn(
                          "mr-2 h-4 w-4",
                          selectedEndpoint === endpoint.name ? "opacity-100" : "opacity-0"
                        )}
                      />
                      <div className="flex-1">
                        <div className="font-medium">{endpoint.name}</div>
                      </div>
                    </div>
                  ))}
                  {searchQuery.trim() && !filteredEndpoints.some(e => e.name === searchQuery.trim()) && (
                    <div
                      className="flex items-center p-2 text-sm cursor-pointer hover:bg-accent hover:text-accent-foreground border-t"
                      onClick={() => handleSelect(searchQuery.trim())}
                    >
                      <div className="flex-1">
                        <div className="font-medium text-blue-600">Use "{searchQuery.trim()}"</div>
                        <div className="text-xs text-gray-500">Enter endpoint name manually</div>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </PopoverContent>
      </Popover>
      </div>
    </TooltipProvider>
  )
}
