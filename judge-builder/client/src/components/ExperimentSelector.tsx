import React, { useState, useEffect, useCallback } from "react"
import { Check, ChevronsUpDown } from "lucide-react"
import { ExperimentsService } from "@/fastapi_client"
import type { ExperimentInfo } from "@/fastapi_client"
import { Button } from "@/components/ui/button"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { cn } from "@/lib/utils"
import { useToast } from "@/hooks/use-toast"

interface ExperimentSelectorProps {
  selectedExperimentId: string
  onExperimentSelect: (experimentId: string) => void
  disabled?: boolean
}

export function ExperimentSelector({ 
  selectedExperimentId, 
  onExperimentSelect, 
  disabled = false 
}: ExperimentSelectorProps) {
  const { toast } = useToast()
  const [allExperiments, setAllExperiments] = useState<ExperimentInfo[]>([])
  const [searchQuery, setSearchQuery] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [comboboxOpen, setComboboxOpen] = useState(false)

  // Fetch experiments (no search API available, so fetch all)
  const fetchExperiments = useCallback(async () => {
    try {
      setIsLoading(true)
      const results = await ExperimentsService.listExperimentsApiExperimentsGet()
      setAllExperiments(results)
    } catch (err) {
      console.error('Error fetching experiments:', err)
      toast({
        title: "Warning",
        description: "Failed to load experiments. You can still enter an experiment ID manually.",
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }, [toast])

  // Handle direct ID input for search
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      // If the search query looks like an experiment ID (numeric), set it directly
      if (searchQuery.trim() && /^\d+$/.test(searchQuery.trim())) {
        onExperimentSelect(searchQuery.trim())
        setComboboxOpen(false)
      }
    }, 300)
    
    return () => clearTimeout(timeoutId)
  }, [searchQuery, onExperimentSelect])

  // Filter experiments based on search query
  const filteredExperiments = allExperiments.filter(exp => {
    if (!searchQuery.trim()) return true
    const query = searchQuery.toLowerCase()
    return (
      exp.name.toLowerCase().includes(query) ||
      exp.experiment_id.includes(query)
    )
  })

  // Load experiments on component mount
  useEffect(() => {
    fetchExperiments()
  }, [fetchExperiments])
  
  const selectedExperiment = allExperiments.find(exp => exp.experiment_id === selectedExperimentId)

  // Extract just the experiment name from the full path
  const getExperimentDisplayName = (fullName: string) => {
    const parts = fullName.split('/')
    return parts[parts.length - 1] || fullName
  }

  return (
    <div className="space-y-2">
      <Popover open={comboboxOpen} onOpenChange={setComboboxOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={comboboxOpen}
            className="w-full justify-between"
            disabled={disabled}
          >
            {selectedExperiment ? (
              <span className="truncate">
                {getExperimentDisplayName(selectedExperiment.name)} ({selectedExperiment.experiment_id})
              </span>
            ) : selectedExperimentId ? (
              <span className="truncate">
                ID: {selectedExperimentId}
              </span>
            ) : (
              "Search experiments or paste experiment ID..."
            )}
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[400px] p-0">
          <div className="flex flex-col">
            <div className="border-b px-3 py-2">
              <input
                type="text"
                placeholder="Search by name or paste experiment ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-2 py-1 text-sm border-0 outline-none bg-transparent"
              />
            </div>
            <div className="max-h-60 overflow-auto">
              {isLoading ? (
                <div className="p-3 text-sm text-center text-muted-foreground">Loading experiments...</div>
              ) : filteredExperiments.length === 0 ? (
                <div className="p-3 text-sm text-center text-muted-foreground">No experiments found</div>
              ) : (
                filteredExperiments.map((experiment) => (
                  <div
                    key={experiment.experiment_id}
                    className="flex items-center p-2 text-sm cursor-pointer hover:bg-accent hover:text-accent-foreground"
                    onClick={() => {
                      onExperimentSelect(experiment.experiment_id)
                      setComboboxOpen(false)
                    }}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        selectedExperimentId === experiment.experiment_id 
                          ? "opacity-100" 
                          : "opacity-0"
                      )}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">{getExperimentDisplayName(experiment.name)}</div>
                      <div className="text-xs text-gray-500">ID: {experiment.experiment_id}</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  )
}