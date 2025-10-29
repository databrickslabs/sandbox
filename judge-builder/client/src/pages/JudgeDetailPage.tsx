import { useState, useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useJudge, useJudgeExamples, useLabelingProgress, useAlignment, useAlignmentComparison, useExperimentTraces } from "@/hooks/useApi"
import { UsersService, AlignmentService, LabelingService, JudgesService } from "@/fastapi_client"
import type { Example, AlignmentModelConfig } from "@/fastapi_client"
import { AlignmentModelSelector } from "@/components/AlignmentModelSelector"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Checkbox } from "@/components/ui/checkbox"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { ArrowLeft, ExternalLink, Plus, RefreshCw, Settings, Database, CheckCircle, ChevronDown, ChevronRight, Play, Tag, Copy, Share2, User, Bot, ArrowRight, AlertTriangle, Check, X, Info } from "lucide-react"
import { LoadingDots } from "@/components/ui/loading-dots"
import { useToast } from "@/contexts/ToastContext"

// Use API types directly from generated client

interface AvailableTrace {
  trace_id: string
  request_id?: string
  request: any
  response: any
}

// Minimum number of labeled examples required for alignment
const MIN_EXAMPLES_FOR_ALIGNMENT = 10

export default function JudgeDetailPage() {
  const { judgeId } = useParams<{ judgeId: string }>()
  const navigate = useNavigate()

  // Fetch data from API
  const { judge, loading: judgeLoading, error: judgeError, refetch: refetchJudge } = useJudge(judgeId)
  const { examples: examplesData, loading: examplesLoading, error: examplesError, refetch: refetchExamples } = useJudgeExamples(judgeId, true)
  const { progress, loading: progressLoading, error: progressError, refetch: refetchProgress } = useLabelingProgress(judgeId)
  const { runAlignment, checkAlignmentStatus, loading: alignmentLoading, needsRefresh } = useAlignment()
  const { data: alignmentData, loading: alignmentDataLoading, error: alignmentDataError, fetchComparison: fetchAlignmentComparison, resetData: resetAlignmentData, retryCount: alignmentRetryCount, hasFetched: alignmentHasFetched } = useAlignmentComparison(judgeId)
  // Preload traces as soon as we have the experiment_id for immediate display when modal opens
  const { traces: availableTraces, loading: tracesLoading, error: tracesError } = useExperimentTraces(judge?.experiment_id)
  
  // Toast for notifications
  const { toast } = useToast()
  

  // Use only API examples, no fallback
  const examples = examplesData?.traces || []

  const [expandedExamples, setExpandedExamples] = useState<Set<string>>(new Set())
  const [expandedComparisons, setExpandedComparisons] = useState<Set<string>>(new Set())
  const [comparisonFilter, setComparisonFilter] = useState<'all' | 'disagreements' | 'version_changes'>('all')
  const [shareModalOpen, setShareModalOpen] = useState(false)
  const [addExamplesModalOpen, setAddExamplesModalOpen] = useState(false)
  const [runIdFilter, setRunIdFilter] = useState("")
  const [selectedTraces, setSelectedTraces] = useState<Set<string>>(new Set())
  const [activeTab, setActiveTab] = useState("examples")
  const [databricksHost, setDatabricksHost] = useState<string | null>(null)
  const [addingExamples, setAddingExamples] = useState(false)
  const [testingTraces, setTestingTraces] = useState<Set<string>>(new Set())
  const [testResults, setTestResults] = useState<Record<string, any>>({})
  const [smeEmails, setSmeEmails] = useState("")
  const [creatingLabelingSession, setCreatingLabelingSession] = useState(false)
  const [alignmentModelConfig, setAlignmentModelConfig] = useState<AlignmentModelConfig | null>(null)

  // Initialize alignment model config when judge is loaded
  useEffect(() => {
    if (judge?.alignment_model_config) {
      setAlignmentModelConfig(judge.alignment_model_config)
    }
  }, [judge?.alignment_model_config])

  // Update alignment model config when it changes
  const handleAlignmentModelConfigChange = async (config: AlignmentModelConfig | null) => {
    setAlignmentModelConfig(config)

    if (!judgeId) return

    try {
      await JudgesService.updateAlignmentModelApiJudgesJudgeIdAlignmentModelPatch(judgeId, config)
      // Refresh judge data
      refetchJudge()
    } catch (error) {
      console.error("Failed to update alignment model config:", error)
      toast({
        title: "Failed to update alignment model",
        description: "Could not save the alignment model configuration.",
        variant: "destructive"
      })
    }
  }

  // Reset labeling session creation state if there was an error or on component mount
  useEffect(() => {
    if (progressError || examplesError) {
      setCreatingLabelingSession(false)
    }
  }, [progressError, examplesError])
  
  // Reset creating state when examples are successfully loaded
  useEffect(() => {
    if (examplesData && !examplesLoading && !examplesError) {
      setCreatingLabelingSession(false)
    }
  }, [examplesData, examplesLoading, examplesError])
  
  
  // Use the labeling session URL from the progress response, fallback to constructed URL
  const shareUrl = progress?.labeling_session_url || `${window.location.origin}/labeling/${judge?.id || judgeId}`
  
  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl)
    } catch (err) {
      console.error('Failed to copy to clipboard:', err)
    }
  }

  const createLabelingSession = async () => {
    if (!judgeId || !smeEmails.trim()) {
      toast({
        title: "Missing information",
        description: "Please provide SME emails",
        variant: "destructive"
      })
      return
    }

    setCreatingLabelingSession(true)
    try {
      const traceIds = examples.map(ex => ex.trace_id)
      const emailList = smeEmails.split(',').map(email => email.trim()).filter(Boolean)
      
      await LabelingService.createLabelingSessionApiLabelingJudgeIdLabelingPost(judgeId, {
        trace_ids: traceIds,
        sme_emails: emailList
      })

      toast({
        title: "Labeling session created",
        description: "Successfully created labeling session and assigned SMEs",
        variant: "success"
      })

      // Clear the input and refresh data
      setSmeEmails("")
      refetchProgress()
      refetchJudge()
    } catch (error) {
      console.error('Failed to create labeling session:', error)
      toast({
        title: "Failed to create labeling session",
        description: "Please try again or check the console for details",
        variant: "destructive"
      })
    }
    
    // Always reset the loading state, even if there were errors in the finally block
    setCreatingLabelingSession(false)
  }
  
  const filteredTraces = availableTraces || []
    
  const toggleTraceSelection = (traceId: string) => {
    const newSelected = new Set(selectedTraces)
    if (newSelected.has(traceId)) {
      newSelected.delete(traceId)
    } else {
      newSelected.add(traceId)
    }
    setSelectedTraces(newSelected)
  }
  
  const toggleSelectAll = () => {
    if (selectedTraces.size === filteredTraces.length) {
      setSelectedTraces(new Set())
    } else {
      setSelectedTraces(new Set(filteredTraces.map(t => t.trace_id)))
    }
  }
  
  const addSelectedExamples = async () => {
    if (!judgeId || selectedTraces.size === 0) {
      return
    }
    
    setAddingExamples(true)
    try {
      const traceIds = Array.from(selectedTraces)
      const response = await LabelingService.addExamplesApiLabelingJudgeIdExamplesPost(judgeId, {
        trace_ids: traceIds
      })
      
      // Refresh examples list, progress, and close modal
      refetchExamples()
      refetchProgress()
      setSelectedTraces(new Set())
      setAddExamplesModalOpen(false)
    } catch (error) {
      console.error('Failed to add examples:', error)
      
      // Close modal immediately on error
      setAddExamplesModalOpen(false)
      
      // Check if this is a "no labeling session" error
      const errorMessage = error instanceof Error ? error.message : String(error)
      const errorString = JSON.stringify(error)
      
      if (errorMessage.includes('No labeling session found for this judge') || 
          errorString.includes('No labeling session found for this judge') ||
          errorString.includes('"detail":"No labeling session found for this judge"')) {
        toast({
          title: "No Labeling Session Found",
          description: "Please create a labeling session first before adding examples.",
          variant: "destructive",
          duration: 6000 // Show for 6 seconds
        })
      } else {
        toast({
          title: "Failed to add examples",
          description: "Could not add examples. Please try again.",
          variant: "destructive",
          duration: 5000 // Show for 5 seconds
        })
      }
    } finally {
      setAddingExamples(false)
    }
  }
  
  const toggleComparisonExpanded = (comparisonId: string) => {
    const newExpanded = new Set(expandedComparisons)
    if (newExpanded.has(comparisonId)) {
      newExpanded.delete(comparisonId)
    } else {
      newExpanded.add(comparisonId)
    }
    setExpandedComparisons(newExpanded)
  }

  const handleRefreshAlignment = async () => {
    if (!judgeId) return
    
    try {
      await checkAlignmentStatus(judgeId)
      // If successful, refresh the judge data and fetch alignment comparison
      refetchJudge()
      fetchAlignmentComparison().catch(error => {
        console.error('Error fetching alignment comparison:', error)
      })
    } catch (error) {
      console.error('Failed to check alignment status:', error)
      toast({
        title: "Failed to check alignment status",
        description: "Please try again or check the app's logs",
        variant: "destructive"
      })
    }
  }

  const testJudgeOnTrace = async (traceId: string) => {
    if (!judgeId) return
    
    setTestingTraces(prev => new Set([...prev, traceId]))
    try {
      const result = await AlignmentService.testJudgeApiAlignmentJudgeIdTestPost(judgeId, {
        trace_id: traceId
      })
      setTestResults(prev => ({ ...prev, [traceId]: result }))
      
      // Refresh examples to show the updated judge assessment in the row
      refetchExamples()
    } catch (error) {
      console.error('Failed to test judge on trace:', error)
      toast({
        title: "Judge Test Failed",
        description: "Failed to test judge on this trace. Please check the app logs for details.",
        variant: "destructive"
      })
    } finally {
      setTestingTraces(prev => {
        const newSet = new Set(prev)
        newSet.delete(traceId)
        return newSet
      })
    }
  }
  
  
  // Calculate examples ready for alignment (labeled but not aligned)
  const labeledExamples = progress?.labeled_examples || 0
  const alignedExamples = progress?.used_for_alignment || 0
  const readyForAlignment = labeledExamples - alignedExamples

  // Determine if align tab should be available
  const isAlignTabAvailable = judge ? (
    (judge.version === 1 && labeledExamples > 0) || 
    (judge.version >= 2)
  ) : false

  // Load Databricks host for experiment links
  useEffect(() => {
    const loadDatabricksHost = async () => {
      try {
        const userInfo = await UsersService.getCurrentUserApiUsersMeGet()
        
        if (userInfo.databricks_host) {
          setDatabricksHost(userInfo.databricks_host)
        }
      } catch (error) {
        console.error('Failed to load user info:', error)
      }
    }
    loadDatabricksHost()
  }, [])

  // Reload labeling progress when page regains focus
  useEffect(() => {
    const handleFocus = () => {
      if (judgeId && refetchProgress) {
        refetchProgress()
      }
    }

    window.addEventListener('focus', handleFocus)
    return () => window.removeEventListener('focus', handleFocus)
  }, [judgeId, refetchProgress])

  // Fetch alignment comparison data when align tab is active and judge version >= 2
  useEffect(() => {
    
    if (activeTab === 'align' && judge?.version && judge.version >= 2 && judgeId && !alignmentData && !alignmentDataLoading && !alignmentHasFetched) {
      fetchAlignmentComparison().catch(error => {
        console.error('Failed to fetch alignment comparison:', error)
      })
    }
  }, [activeTab, judge?.version, judgeId, alignmentData, alignmentDataLoading, alignmentHasFetched, fetchAlignmentComparison])


  // Open experiment in Databricks
  const openExperimentLink = (experimentId: string) => {
    if (databricksHost) {
      const url = `${databricksHost}/ml/experiments/${experimentId}`
      window.open(url, '_blank')
    }
  }

  // Handle loading states
  if (judgeLoading || !judge) {
    return (
      <div className="container mx-auto p-6 max-w-6xl">
        <div className="flex items-center justify-center min-h-[200px]">
          <div className="text-center">
            <div className="flex items-center justify-center gap-2 text-muted-foreground">
              <span>Loading judge details</span>
              <LoadingDots size="sm" />
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Handle errors
  if (judgeError) {
    return (
      <div className="container mx-auto p-6 max-w-6xl">
        <div className="flex items-center justify-center min-h-[200px]">
          <div className="text-center">
            <p className="text-red-600 mb-4">Error loading judge: {judgeError}</p>
            <Button onClick={() => navigate("/")}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Judges
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex-1">
          <Button variant="ghost" size="sm" onClick={() => navigate("/")}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Judges
          </Button>
        </div>
        
        <div className="flex items-center gap-3">
          <Settings className="w-8 h-8" />
          <h1 className="text-4xl font-bold">Judge Builder: {judge?.name}</h1>
          <Badge variant="secondary">v{judge?.version || 1}</Badge>
        </div>
        
        <div className="flex-1"></div> {/* Equal spacing on right */}
      </div>

      {/* Experiment Box - Centered Below */}
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-1 bg-muted px-2 py-1 rounded text-sm">
          <span className="text-muted-foreground">Experiment:</span>
          <span className="font-mono">{judge?.experiment_id}</span>
          {databricksHost && (
            <Button
              size="sm"
              variant="ghost"
              className="h-4 w-4 p-0 hover:bg-gray-200"
              onClick={() => openExperimentLink(judge?.experiment_id!)}
              title="Open in Databricks"
            >
              <ExternalLink className="h-3 w-3" />
            </Button>
          )}
        </div>
      </div>

      {/* Judge Instructions */}
      <div className="mb-6 p-4 bg-muted/30 rounded-lg border">
        <h3 className="font-semibold mb-2">Judge Instructions</h3>
        <p className="text-muted-foreground">{judge?.instruction}</p>
      </div>

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="examples" className="flex items-center gap-2">
            <Database className="w-4 h-4" />
            Manage Examples
          </TabsTrigger>
          <TabsTrigger 
            value="align" 
            className={`flex items-center gap-2 ${!isAlignTabAvailable ? 'opacity-50 cursor-not-allowed' : ''}`}
            disabled={!isAlignTabAvailable}
            onClick={(e) => {
              if (!isAlignTabAvailable) {
                e.preventDefault()
                toast({
                  title: "Alignment not available",
                  description: "You need to add labeled examples before aligning",
                  variant: "destructive"
                })
              }
            }}
          >
            <CheckCircle className="w-4 h-4" />
            Align
          </TabsTrigger>
        </TabsList>

        {/* Manage Examples Tab */}
        <TabsContent value="examples" className="space-y-6">
          
          {/* Examples Section */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Database className="w-5 h-5" />
                  <CardTitle>Examples</CardTitle>
                  <Badge variant="secondary" className="bg-blue-100 text-blue-800 border-blue-200">
                    {examplesData?.count || 0} traces
                  </Badge>
                </div>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="outline" onClick={() => setAddExamplesModalOpen(true)}>
                    <Plus className="w-4 h-4 mr-1" />
                  </Button>
                  <Button size="sm" variant="outline" onClick={refetchExamples} disabled={examplesLoading}>
                    <RefreshCw className={`w-4 h-4 ${examplesLoading ? 'animate-spin' : ''}`} />
                  </Button>
                </div>
              </div>
              <CardDescription>Manage the set of examples for this judge.</CardDescription>
            </CardHeader>
            <CardContent>
              {examplesError && (
                <div className="text-red-600 text-sm mb-4 p-3 bg-red-50 border border-red-200 rounded">
                  Error loading examples: {examplesError}
                </div>
              )}
              <div className="space-y-3 max-h-96 overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
                {examplesLoading && examples.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <div className="flex items-center justify-center gap-2">
                      <span>Loading examples</span>
                      <LoadingDots size="sm" />
                    </div>
                  </div>
                ) : (
                  examples.map((example) => {
                  const isExpanded = expandedExamples.has(example.trace_id)
                  
                  const toggleExpanded = () => {
                    const newExpanded = new Set(expandedExamples)
                    if (isExpanded) {
                      newExpanded.delete(example.trace_id)
                    } else {
                      newExpanded.add(example.trace_id)
                    }
                    setExpandedExamples(newExpanded)
                  }

                  return (
                    <div key={example.trace_id} className="border rounded-lg p-4 space-y-3 cursor-pointer hover:bg-muted/30 transition-colors" onClick={toggleExpanded}>
                      {/* Collapsed View - Always visible */}
                      <div className="flex items-center gap-3">
                        <div 
                          className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-mono cursor-pointer hover:bg-blue-200 flex items-center gap-1"
                          onClick={(e) => {
                            e.stopPropagation()
                            if (databricksHost && judge?.experiment_id) {
                              const traceUrl = `${databricksHost}/ml/experiments/${judge.experiment_id}/traces?selectedEvaluationId=${example.trace_id}`
                              window.open(traceUrl, '_blank')
                            }
                          }}
                          title={`Open trace ${example.trace_id} in new tab`}
                        >
                          <span>{example.trace_id.length > 12 ? `${example.trace_id.substring(0, 12)}...` : example.trace_id}</span>
                          <ExternalLink className="w-3 h-3" />
                        </div>
                        <span className="text-sm flex-1">{example.request}</span>
                        <div className="flex items-center gap-2">
                          {/* Judge Assessment Icon - Prioritize fresh test results over API assessments */}
                          {(testResults[example.trace_id] || example.judge_assessment) && !testingTraces.has(example.trace_id) && (
                            <div className="flex items-center">
                              {(() => {
                                // Prioritize fresh test result over API assessment
                                const testResult = testResults[example.trace_id]
                                const apiAssessment = example.judge_assessment
                                
                                let feedback, error
                                if (testResult) {
                                  // Test result is TestJudgeResponse with feedback: Feedback
                                  feedback = testResult.feedback?.feedback
                                  error = testResult.feedback?.error
                                } else if (apiAssessment) {
                                  // API assessment is directly a Feedback object
                                  feedback = apiAssessment.feedback
                                  error = apiAssessment.error
                                } else {
                                  return null
                                }
                                
                                // Check for error first
                                if (error) {
                                  return (
                                    <div className="px-2 py-1 rounded-full bg-yellow-100 text-yellow-700 text-xs font-medium">
                                      Error
                                    </div>
                                  )
                                }
                                
                                // Get feedback value
                                const feedbackValue = feedback?.value
                                if (!feedbackValue) return null
                                
                                // Display pass/fail icon
                                if (feedbackValue.toLowerCase() === 'pass') {
                                  return (
                                    <div className="px-2 py-1 rounded-full bg-green-100 text-green-700 text-xs font-medium">
                                      Pass
                                    </div>
                                  )
                                } else if (feedbackValue.toLowerCase() === 'fail') {
                                  return (
                                    <div className="px-2 py-1 rounded-full bg-red-100 text-red-700 text-xs font-medium">
                                      Fail
                                    </div>
                                  )
                                }
                                return null
                              })()}
                            </div>
                          )}
                          
                          <div className="bg-blue-50 border border-blue-200 rounded-md px-2 py-1" onClick={(e) => e.stopPropagation()}>
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="text-blue-600 hover:text-blue-700 hover:bg-blue-100 h-auto px-2 py-1 text-xs"
                              onClick={() => testJudgeOnTrace(example.trace_id)}
                              disabled={testingTraces.has(example.trace_id)}
                              title="Test judge on this example"
                            >
                              {testingTraces.has(example.trace_id) ? (
                                <div className="flex items-center gap-1">
                                  <span>Testing...</span>
                                  <LoadingDots size="sm" />
                                </div>
                              ) : (
                                <div className="flex items-center gap-1">
                                  <span>Run judge</span>
                                  <Play className="w-3 h-3" />
                                </div>
                              )}
                            </Button>
                          </div>
                        </div>
                        <div className="p-2">
                          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                        </div>
                      </div>
                      
                      {/* Expanded View - Only when expanded */}
                      {isExpanded && (
                        <div className="space-y-3 pt-3 border-t">
                          <div>
                            <h5 className="text-sm font-semibold mb-1">Response</h5>
                            <p className="text-sm text-muted-foreground">{example.response}</p>
                          </div>
                          
                          {/* Judge Assessment - Prioritize fresh test results over API assessments */}
                          {(testResults[example.trace_id] || example.judge_assessment) && (
                            <div>
                              <h5 className="text-sm font-semibold mb-1">Judge Assessment</h5>
                              <div className="bg-gray-50 border rounded-md p-2">
                                {(() => {
                                  // Prioritize fresh test result over API assessment
                                  const testResult = testResults[example.trace_id]
                                  const apiAssessment = example.judge_assessment
                                  
                                  let feedback, error, rationale
                                  if (testResult) {
                                    // Test result is TestJudgeResponse with feedback: Feedback
                                    feedback = testResult.feedback?.feedback
                                    error = testResult.feedback?.error
                                    rationale = testResult.feedback?.rationale
                                  } else if (apiAssessment) {
                                    // API assessment is directly a Feedback object
                                    feedback = apiAssessment.feedback
                                    error = apiAssessment.error
                                    rationale = apiAssessment.rationale
                                  } else {
                                    return null
                                  }
                                  
                                  // Check for error first
                                  if (error) {
                                    return (
                                      <div className="text-sm">
                                        <div className="flex items-center gap-2">
                                          <div className="px-2 py-1 rounded-full bg-yellow-100 text-yellow-700 text-xs font-medium">
                                            Error
                                          </div>
                                          <span className="text-sm text-yellow-600">Judge evaluation failed</span>
                                        </div>
                                      </div>
                                    )
                                  }
                                  
                                  const feedbackValue = feedback?.value
                                  if (!feedbackValue) return null
                                  
                                  const isPass = feedbackValue.toLowerCase() === 'pass'
                                  const isFail = feedbackValue.toLowerCase() === 'fail'
                                  
                                  return (
                                    <div className="text-sm space-y-2">
                                      <div className="flex items-center gap-2">
                                        <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                                          isPass ? 'bg-green-100 text-green-700' : 
                                          isFail ? 'bg-red-100 text-red-700' : 
                                          'bg-gray-100 text-gray-700'
                                        }`}>
                                          {feedbackValue}
                                        </div>
                                      </div>
                                      {rationale && (
                                        <div>
                                          <span className="font-medium text-gray-700">Rationale: </span>
                                          <span className="text-gray-600">{rationale}</span>
                                        </div>
                                      )}
                                    </div>
                                  )
                                })()}
                              </div>
                            </div>
                          )}
                          
                          {(example.judgment || example.rationale) && (
                            <div className="flex gap-6">
                              {example.judgment && (
                                <div>
                                  <h5 className="text-sm font-semibold mb-1">Result</h5>
                                  <Badge variant={example.judgment === "pass" ? "default" : "destructive"} className={example.judgment === "pass" ? "bg-green-500 text-white" : ""}>
                                    {example.judgment}
                                  </Badge>
                                </div>
                              )}
                              
                              {example.rationale && (
                                <div className="flex-1">
                                  <h5 className="text-sm font-semibold mb-1">Rationale</h5>
                                  <p className="text-sm text-muted-foreground">{example.rationale}</p>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })
                )}
                {!examplesLoading && examples.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    Please add {MIN_EXAMPLES_FOR_ALIGNMENT} or more examples to start aligning this judge.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Labeling Section */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Tag className="w-5 h-5" />
                  <CardTitle>Labeling</CardTitle>
                </div>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="outline" onClick={refetchProgress} disabled={progressLoading}>
                    <RefreshCw className={`w-4 h-4 ${progressLoading ? 'animate-spin' : ''}`} />
                  </Button>
                </div>
              </div>
              <CardDescription>Manage your active labeling session and view progress</CardDescription>
            </CardHeader>
            <CardContent>
              {progressError && (
                <div className="text-red-600 text-sm mb-4 p-3 bg-red-50 border border-red-200 rounded">
                  Error loading progress: {progressError}
                </div>
              )}
              {progressLoading ? (
                <div className="text-center py-8 text-muted-foreground">
                  <div className="flex items-center justify-center gap-2">
                    <span>Loading progress</span>
                    <LoadingDots size="sm" />
                  </div>
                </div>
              ) : progress?.assigned_smes && progress.assigned_smes.length > 0 ? (
                <div className="space-y-4">
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <span className="text-sm text-blue-900">Assigned to: </span>
                        <span className="text-sm font-bold text-blue-900">
                          {progress.assigned_smes.join(', ')}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button size="sm" variant="outline" onClick={() => setShareModalOpen(true)} className="border-blue-500 text-blue-600 hover:bg-blue-50">
                          <Share2 className="w-3 h-3 mr-1" />
                          Share
                        </Button>
                        <Button 
                          size="sm" 
                          variant="outline" 
                          className="border"
                          onClick={() => {
                            const url = progress?.labeling_session_url
                            if (url) {
                              window.open(url, '_blank')
                            } else {
                              console.error('No labeling session URL available')
                            }
                          }}
                          disabled={!progress?.labeling_session_url}
                        >
                          <ExternalLink className="w-3 h-3 mr-1" />
                          Open
                        </Button>
                      </div>
                    </div>
                    
                    {/* Progress Bar */}
                    <div className="space-y-3">
                      <div>
                        <div className="flex justify-between text-sm mb-3 text-blue-900">
                          <span>Labeling Progress</span>
                          <span>
                            {progress && progress.total_examples > 0 
                              ? `${progress.labeled_examples} out of ${progress.total_examples} (${Math.round((progress.labeled_examples / progress.total_examples) * 100)}%) labeled` 
                              : '0 out of 0 (0%) labeled'}, 
                            {progress && progress.total_examples > 0 
                              ? ` ${readyForAlignment} (${Math.round((readyForAlignment / progress.total_examples) * 100)}%) to be aligned` 
                              : ' 0 (0%) to be aligned'}
                          </span>
                        </div>
                        <div className="w-full bg-gray-300 rounded-full h-3 relative">
                          {/* Green bar for aligned examples */}
                          <div className="bg-green-500 h-3 rounded-full absolute left-0 top-0" style={{ 
                            width: `${progress && progress.total_examples > 0 ? Math.round((alignedExamples / progress.total_examples) * 100) : 0}%` 
                          }}></div>
                          {/* Blue bar for labeled but not aligned examples */}
                          <div className="bg-blue-600 h-3 rounded-full absolute top-0" style={{ 
                            left: `${progress && progress.total_examples > 0 ? Math.round((alignedExamples / progress.total_examples) * 100) : 0}%`,
                            width: `${progress && progress.total_examples > 0 ? Math.round((readyForAlignment / progress.total_examples) * 100) : 0}%` 
                          }}></div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-4 text-xs">
                        <div className="flex items-center gap-1">
                          <div className="w-3 h-3 rounded-full bg-green-500"></div>
                          <span className="text-blue-800">Judge aligned on</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                          <span className="text-blue-800">Labeled</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <div className="w-3 h-3 rounded-full bg-gray-400"></div>
                          <span className="text-blue-800">Unlabeled</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-3">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-blue-900">
                      Assign Subject Matter Experts
                    </label>
                    <Input
                      placeholder="user1@example.com, user2@example.com"
                      value={smeEmails}
                      onChange={(e) => setSmeEmails(e.target.value)}
                      className="text-sm"
                    />
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={createLabelingSession}
                        disabled={!smeEmails.trim() || creatingLabelingSession}
                        className="text-xs"
                        title={
                          !smeEmails.trim() ? "Please enter SME emails" :
                          creatingLabelingSession ? "Creating session..." :
                          "Ready to create labeling session"
                        }
                      >
                        {creatingLabelingSession ? (
                          <>
                            Creating
                            <LoadingDots size="sm" />
                          </>
                        ) : (
                          'Create Labeling Session'
                        )}
                      </Button>
                    </div>
                    <p className="text-xs text-blue-700">
                      Enter comma-separated email addresses of SMEs who will label examples
                    </p>
                  </div>
                </div>
              )}
              
              {/* Note about removing feedback - moved outside blue box */}
              <div className="text-xs text-gray-600 mt-3 p-2 bg-gray-50 rounded">
                <strong>Note:</strong> To remove feedback, please view the trace in the trace UI and delete the feedback assessment provided by your labeler.
              </div>
            </CardContent>
          </Card>
          
          {/* Navigation Button */}
          <div className="flex justify-end pt-6">
            <Button 
              onClick={async () => {
                if (readyForAlignment === 0) {
                  toast({
                    title: "Not enough examples for alignment",
                    description: `Please add ${MIN_EXAMPLES_FOR_ALIGNMENT} or more examples to start aligning the judge.`,
                    variant: "destructive"
                  })
                  return
                }
                
                if (judgeId && judge?.experiment_id) {
                  // First redirect to align tab
                  setActiveTab("align")
                  
                  try {
                    // Reset alignment data before running alignment to prevent stale data
                    resetAlignmentData()
                    
                    // Then run alignment
                    await runAlignment(judgeId, judge.experiment_id)
                    // Refresh judge data to get new version
                    refetchJudge()
                    // Refresh alignment comparison data
                    fetchAlignmentComparison().catch(error => {
                      console.error('Error fetching alignment comparison after runAlignment:', error)
                    })
                  } catch (error) {
                    console.error('Failed to run alignment:', error)
                    
                    // Check if this is an insufficient examples error
                    const errorMessage = error instanceof Error ? error.message : String(error)
                    const errorString = JSON.stringify(error)
                    const isInsufficientExamples = (
                      errorMessage.includes('Insufficient labeled examples') ||
                      errorMessage.includes('need at least') ||
                      errorString.includes('Insufficient labeled examples') ||
                      errorString.includes('need at least')
                    )
                    
                    if (isInsufficientExamples) {
                      toast({
                        title: "Not Enough Labeled Examples",
                        description: `Please add ${MIN_EXAMPLES_FOR_ALIGNMENT} or more examples to start aligning the judge.`,
                        variant: "destructive",
                        duration: 8000
                      })
                      return
                    }
                    
                    // Check if this is an optimization failure
                    const isOptimizationFailure = errorMessage.includes('Judge optimization failed') || errorMessage.includes('422')
                    
                    if (isOptimizationFailure) {
                      toast({
                        title: "Judge Optimization Failed",
                        description: errorMessage.includes('Judge optimization failed') 
                          ? errorMessage.replace('Judge optimization failed: ', '') 
                          : errorMessage,
                        variant: "destructive",
                        duration: 15000 // Show for 15 seconds
                      })
                    } else if (needsRefresh) {
                      toast({
                        title: "Alignment may have completed",
                        description: "Polling timed out but alignment may be done. Click refresh to check status.",
                        variant: "destructive",
                        action: (
                          <Button 
                            onClick={handleRefreshAlignment} 
                            variant="outline" 
                            size="sm"
                            className="flex items-center gap-2"
                          >
                            <RefreshCw className="w-4 h-4" />
                            Refresh
                          </Button>
                        )
                      })
                    } else {
                      toast({
                        title: "Alignment failed",
                        description: "Please check the app logs for details.",
                        variant: "destructive"
                      })
                    }
                  }
                }
              }} 
              className={`flex items-center gap-2 ${readyForAlignment === 0 ? 'opacity-50' : ''}`}
              disabled={alignmentLoading}
            >
              {alignmentLoading ? (
                <>
                  <LoadingDots size="sm" />
                  Running alignment...
                </>
              ) : (
                <>
                  {readyForAlignment === 0 ? 'Align' : `Align on ${readyForAlignment} examples`}
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </Button>
          </div>
        </TabsContent>

        {/* Align Judge Tab */}
        <TabsContent value="align" className="space-y-6">
          
          {/* Show loading state during alignment */}
          {alignmentLoading && (
            <div className="text-center py-12">
              <div className="space-y-4">
                <div className="flex items-center justify-center">
                  <LoadingDots size="lg" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold">Running alignment</h3>
                  <p className="text-sm text-muted-foreground">Please check back in a bit. Alignment takes a few minutes to run.</p>
                </div>
              </div>
            </div>
          )}
          
          {/* Show alignment comparison loading state */}
          {!alignmentLoading && alignmentDataLoading && (
            <div className="text-center py-12">
              <div className="space-y-4">
                <div className="flex items-center justify-center">
                  <LoadingDots size="lg" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold">Loading alignment results</h3>
                </div>
              </div>
            </div>
          )}

          {/* Show alignment comparison error state */}
          {!alignmentLoading && !alignmentDataLoading && alignmentDataError && (
            <div className="text-center py-12">
              <div className="space-y-4">
                <div className="text-red-500">
                  <AlertTriangle className="w-12 h-12 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold">Failed to load alignment results</h3>
                  <p className="text-sm text-muted-foreground">{alignmentDataError}</p>
                </div>
                <Button onClick={() => fetchAlignmentComparison()} variant="outline">
                  Try Again
                </Button>
              </div>
            </div>
          )}

          {/* Show content when not loading and no error */}
          {!alignmentLoading && !alignmentDataLoading && !alignmentDataError && (
            <>
              {judge?.version === 1 ? (
                /* Centered align section for v1 judges */
                <div className="flex flex-col items-center justify-center py-16 space-y-6">
                  <div className="text-center space-y-4">
                    <h2 className="text-3xl font-bold text-gray-900">Align your judge</h2>
                    <p className="text-lg text-muted-foreground max-w-md">
                      Improve your judge's performance by running alignment with human feedback.
                    </p>
                  </div>

                  <div className="w-full max-w-md">
                    <AlignmentModelSelector
                      value={alignmentModelConfig}
                      onChange={handleAlignmentModelConfigChange}
                      showTooltip={true}
                    />
                  </div>

                  <Button 
                    size="lg"
                    className={`flex items-center gap-2 ${readyForAlignment === 0 ? 'opacity-50' : ''}`} 
                    onClick={async () => {
                      if (readyForAlignment === 0) {
                        toast({
                          title: "Not enough examples for alignment",
                          description: `Please add ${MIN_EXAMPLES_FOR_ALIGNMENT} or more examples to start aligning the judge.`,
                          variant: "destructive"
                        })
                        return
                      }
                      
                      if (judgeId && judge?.experiment_id) {
                        try {
                          // Reset alignment data before running alignment to prevent stale data
                          resetAlignmentData()
                          
                          // Run alignment (already on align tab)
                          await runAlignment(judgeId, judge.experiment_id)
                          // Refresh judge data to get new version
                          refetchJudge()
                          // Refresh alignment comparison data
                          fetchAlignmentComparison().catch(error => {
                            console.error('Error fetching alignment comparison after runAlignment:', error)
                          })
                        } catch (error) {
                          console.error('Failed to run alignment:', error)
                          
                          // Check if this is an insufficient examples error
                          const errorMessage = error instanceof Error ? error.message : String(error)
                          const errorString = JSON.stringify(error)
                          const isInsufficientExamples = (
                            errorMessage.includes('Insufficient labeled examples') ||
                            errorMessage.includes('need at least') ||
                            errorString.includes('Insufficient labeled examples') ||
                            errorString.includes('need at least')
                          )
                          
                          if (isInsufficientExamples) {
                            toast({
                              title: "Not Enough Labeled Examples",
                              description: `Please add ${MIN_EXAMPLES_FOR_ALIGNMENT} or more examples to start aligning the judge.`,
                              variant: "destructive",
                              duration: 8000
                            })
                            return
                          }
                          
                          // Check if this is an optimization failure
                          const isOptimizationFailure = errorMessage.includes('Judge optimization failed') || errorMessage.includes('422')
                          
                          if (isOptimizationFailure) {
                            toast({
                              title: "Judge Optimization Failed",
                              description: errorMessage.includes('Judge optimization failed') 
                                ? errorMessage.replace('Judge optimization failed: ', '') 
                                : errorMessage,
                              variant: "destructive",
                              duration: 15000 // Show for 15 seconds
                            })
                          } else if (needsRefresh) {
                            toast({
                              title: "Alignment may have completed",
                              description: "Polling timed out but alignment may be done. Click refresh to check status.",
                              variant: "destructive",
                              action: (
                                <Button 
                                  onClick={handleRefreshAlignment} 
                                  variant="outline" 
                                  size="sm"
                                  className="flex items-center gap-2"
                                >
                                  <RefreshCw className="w-4 h-4" />
                                  Refresh
                                </Button>
                              )
                            })
                          } else {
                            toast({
                              title: "Alignment failed",
                              description: "Please check the app logs for details.",
                              variant: "destructive"
                            })
                          }
                        }
                      }
                    }}
                    disabled={alignmentLoading}
                  >
                    <Play className="w-5 h-5" />
                    {alignmentLoading ? 'Aligning...' : (readyForAlignment === 0 ? 'Align' : 'Align Judge')}
                  </Button>
                </div>
              ) : (
                /* Regular header layout for v2+ judges */
                <div className="space-y-6">
                  {/* Align Section Header with inline model selector */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <h2 className="text-xl font-semibold flex items-center gap-2">
                        <CheckCircle className="w-5 h-5" />
                        Align
                      </h2>
                      {judge?.version && judge.version >= 2 && (
                        <div className="flex items-center gap-2 bg-blue-50 border border-blue-200 px-3 py-1 rounded-lg">
                          <Badge variant="outline" className="text-sm font-semibold bg-white">v{judge.version - 1}</Badge>
                          <span className="text-sm font-semibold text-blue-700">→</span>
                          <Badge variant="outline" className="text-sm font-semibold bg-white">v{judge.version}</Badge>
                        </div>
                      )}
                    </div>

                    {/* Inline Alignment Model Selector */}
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-1">
                        <TooltipProvider>
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
                        </TooltipProvider>
                        <span className="text-sm font-medium text-muted-foreground">Alignment Model:</span>
                      </div>
                      <div className="w-64">
                        <AlignmentModelSelector
                          value={alignmentModelConfig}
                          onChange={handleAlignmentModelConfigChange}
                          showLabel={false}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          
              {/* Show alignment results for version >= 2 */}
              {judge?.version && judge.version >= 2 && alignmentData && !alignmentLoading && (
                <>
                  {/* Top Summary Cards */}
                  <div className="grid grid-cols-3 gap-4">
                    <Card className="text-center">
                      <CardContent className="p-4">
                        <div className="text-2xl font-bold">
                          {(() => {
                            const prevRate = ((alignmentData.metrics.previous_agreement_count / alignmentData.metrics.total_samples) * 100);
                            const newRate = ((alignmentData.metrics.new_agreement_count / alignmentData.metrics.total_samples) * 100);
                            
                            if (alignmentData.metrics.previous_agreement_count > 0) {
                              return (
                                <span className="text-blue-600">{prevRate.toFixed(1)}% → {newRate.toFixed(1)}%</span>
                              );
                            } else {
                              return <span className="text-blue-600">0% → 0%</span>;
                            }
                          })()}
                        </div>
                        <div className="text-sm text-muted-foreground">Alignment</div>
                      </CardContent>
                    </Card>
                    <Card className="text-center">
                      <CardContent className="p-4">
                        <div className="text-3xl font-bold text-blue-600">{alignmentData.metrics.total_samples}</div>
                        <div className="text-sm text-muted-foreground">Total Examples</div>
                      </CardContent>
                    </Card>
                    <Card className={`text-center ${(() => {
                      const prev = alignmentData.metrics.previous_agreement_count;
                      const current = alignmentData.metrics.new_agreement_count;
                      const diff = current - prev;
                      if (diff > 0) return 'bg-green-50 border-green-200';
                      if (diff < 0) return 'bg-red-50 border-red-200';
                      return 'bg-gray-50 border-gray-200';
                    })()}`}>
                      <CardContent className="p-4">
                        <div className="text-2xl font-bold">
                          {(() => {
                            const prev = alignmentData.metrics.previous_agreement_count;
                            const current = alignmentData.metrics.new_agreement_count;
                            const diff = current - prev;
                            const prevRate = ((prev / alignmentData.metrics.total_samples) * 100);
                            const newRate = ((current / alignmentData.metrics.total_samples) * 100);
                            const rateDiff = newRate - prevRate;
                            
                            const diffText = diff >= 0 ? `+${diff}` : `${diff}`;
                            const rateDiffText = rateDiff >= 0 ? `+${rateDiff.toFixed(1)}%` : `${rateDiff.toFixed(1)}%`;
                            const textColor = diff >= 0 ? 'text-green-600' : 'text-red-600';
                            
                            return (
                              <div className={textColor}>{diffText} ({rateDiffText})</div>
                            );
                          })()}
                        </div>
                        <div className="text-sm text-muted-foreground">Alignment Delta</div>
                      </CardContent>
                    </Card>
                  </div>
                </>
              )}

              {/* Confusion Matrix - Only for Binary Outcomes */}
              {judge?.version && judge.version >= 2 && alignmentData && !alignmentLoading && alignmentData.metrics.schema_info?.is_binary && alignmentData.metrics.confusion_matrix_previous && alignmentData.metrics.confusion_matrix_new && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Confusion Matrix</h3>
                  <p className="text-sm text-muted-foreground">Binary outcome analysis showing classification accuracy</p>
                  <div className="space-y-2">
                    <div className="flex gap-4">
                      <div className="flex-1 bg-green-50 border border-green-200 p-3 rounded-lg">
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="text-sm font-semibold text-green-700">True Positives</div>
                            <div className="text-[10px] text-muted-foreground">Judge: Pass, Human: Pass</div>
                          </div>
                          <div className="text-2xl font-bold text-green-600">
                            {alignmentData.metrics.confusion_matrix_previous.true_positive} → {alignmentData.metrics.confusion_matrix_new.true_positive}
                          </div>
                        </div>
                      </div>
                      <div className="flex-1 bg-orange-50 border border-orange-200 p-3 rounded-lg">
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="text-sm font-semibold text-orange-700">False Negatives</div>
                            <div className="text-[10px] text-muted-foreground">Judge: Fail, Human: Pass</div>
                          </div>
                          <div className="text-2xl font-bold text-orange-600">
                            {alignmentData.metrics.confusion_matrix_previous.false_negative} → {alignmentData.metrics.confusion_matrix_new.false_negative}
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-4">
                      <div className="flex-1 bg-red-50 border border-red-200 p-3 rounded-lg">
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="text-sm font-semibold text-red-700">False Positives</div>
                            <div className="text-[10px] text-muted-foreground">Judge: Pass, Human: Fail</div>
                          </div>
                          <div className="text-2xl font-bold text-red-600">
                            {alignmentData.metrics.confusion_matrix_previous.false_positive} → {alignmentData.metrics.confusion_matrix_new.false_positive}
                          </div>
                        </div>
                      </div>
                      <div className="flex-1 bg-gray-50 border border-gray-200 p-3 rounded-lg">
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="text-sm font-semibold text-gray-700">True Negatives</div>
                            <div className="text-[10px] text-muted-foreground">Judge: Fail, Human: Fail</div>
                          </div>
                          <div className="text-2xl font-bold text-gray-600">
                            {alignmentData.metrics.confusion_matrix_previous.true_negative} → {alignmentData.metrics.confusion_matrix_new.true_negative}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}


              {/* Row-by-Row Comparison */}
              {judge?.version && judge.version >= 2 && alignmentData && alignmentData.comparisons && !alignmentLoading && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-semibold">Row-by-Row Comparison</h3>
                      <p className="text-sm text-muted-foreground">Detailed view of human labels vs judge predictions for each trace</p>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            const filteredComparisons = alignmentData.comparisons.filter((comparison: any) => {
                              if (comparisonFilter === 'disagreements') {
                                return comparison.human_feedback?.feedback?.value?.toLowerCase() !== comparison.new_judge_feedback?.feedback?.value?.toLowerCase()
                              }
                              if (comparisonFilter === 'version_changes') {
                                return comparison.previous_judge_feedback?.feedback?.value?.toLowerCase() !== comparison.new_judge_feedback?.feedback?.value?.toLowerCase()
                              }
                              return true
                            })
                            setExpandedComparisons(new Set(filteredComparisons.map((c: any) => c.trace_id)))
                          }}
                          className="text-xs"
                        >
                          Expand All
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setExpandedComparisons(new Set())}
                          className="text-xs"
                        >
                          Collapse All
                        </Button>
                      </div>
                      <div className="flex items-center gap-2">
                        <label className="text-sm font-medium">Filter:</label>
                        <select 
                          value={comparisonFilter}
                          onChange={(e) => setComparisonFilter(e.target.value as 'all' | 'disagreements' | 'version_changes')}
                          className="px-3 py-1 border border-gray-300 rounded-md text-sm bg-white"
                        >
                          <option value="all">All ({alignmentData.comparisons.length})</option>
                          <option value="disagreements">Disagreements ({alignmentData.comparisons.filter((c: any) => c.human_feedback?.feedback?.value?.toLowerCase() !== c.new_judge_feedback?.feedback?.value?.toLowerCase()).length})</option>
                          <option value="version_changes">Version Disagreements ({alignmentData.comparisons.filter((c: any) => c.previous_judge_feedback?.feedback?.value?.toLowerCase() !== c.new_judge_feedback?.feedback?.value?.toLowerCase()).length})</option>
                        </select>
                      </div>
                    </div>
                  </div>
                  <div className="space-y-3">
                      {alignmentData.comparisons
                        .filter((comparison: any) => {
                          if (comparisonFilter === 'disagreements') {
                            return comparison.human_feedback?.feedback?.value?.toLowerCase() !== comparison.new_judge_feedback?.feedback?.value?.toLowerCase()
                          }
                          if (comparisonFilter === 'version_changes') {
                            return comparison.previous_judge_feedback?.feedback?.value?.toLowerCase() !== comparison.new_judge_feedback?.feedback?.value?.toLowerCase()
                          }
                          return true
                        })
                        .map((comparison: any) => {
                        const isExpanded = expandedComparisons.has(comparison.trace_id)
                  
                          const humanRating = comparison.human_feedback?.feedback?.value?.toLowerCase() || 'unknown'
                          const newJudgeRating = comparison.new_judge_feedback?.feedback?.value?.toLowerCase() || 'unknown'
                          const previousJudgeRating = comparison.previous_judge_feedback?.feedback?.value?.toLowerCase() || 'unknown'
                  
                          return (
                            <div key={comparison.trace_id} className="border rounded-lg p-4 space-y-3 cursor-pointer hover:bg-muted/30 transition-colors" onClick={() => toggleComparisonExpanded(comparison.trace_id)}>
                              {/* Collapsed View */}
                              <div className="flex items-center gap-3">
                                <div 
                                  className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-mono cursor-pointer hover:bg-blue-200 flex items-center gap-1"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    if (databricksHost && judge?.experiment_id) {
                                      const traceUrl = `${databricksHost}/ml/experiments/${judge.experiment_id}/traces?selectedEvaluationId=${comparison.trace_id}`
                                      window.open(traceUrl, '_blank')
                                    }
                                  }}
                                  title={`Open trace ${comparison.trace_id} in new tab`}
                                >
                                  <span>{comparison.trace_id.length > 12 ? `${comparison.trace_id.substring(0, 12)}...` : comparison.trace_id}</span>
                                  <ExternalLink className="w-3 h-3" />
                                </div>
                                <span className="text-sm flex-1">{comparison.request}</span>
                                
                                {/* Version Agreement Indicators */}
                                <div className="flex items-center gap-2">
                                  {/* Previous Judge Version Agreement */}
                                  <div className={`px-2 py-1 rounded text-xs font-medium flex items-center ${previousJudgeRating === humanRating ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                                    {previousJudgeRating === humanRating ? (
                                      <Check className="w-3 h-3" />
                                    ) : (
                                      <X className="w-3 h-3" />
                                    )}
                                  </div>
                                  
                                  <ArrowRight className="w-3 h-3 text-gray-400" />
                                  
                                  {/* New Judge Version Agreement */}
                                  <div className={`px-2 py-1 rounded text-xs font-medium flex items-center ${newJudgeRating === humanRating ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                                    {newJudgeRating === humanRating ? (
                                      <Check className="w-3 h-3" />
                                    ) : (
                                      <X className="w-3 h-3" />
                                    )}
                                  </div>
                                </div>
                                
                                <div className="p-2">
                                  {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                                </div>
                              </div>
                      
                              {/* Expanded View */}
                              {isExpanded && (
                                <div className="space-y-4 pt-3 border-t">
                                  <div>
                                    <h5 className="text-sm font-semibold mb-1">Response</h5>
                                    <p className="text-sm text-muted-foreground">{comparison.response}</p>
                                  </div>
                                  
                                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                    {/* Human Rating */}
                                    <div className="space-y-2">
                                      <div className="flex items-center gap-2">
                                        <User className="w-4 h-4" />
                                        <h5 className="text-sm font-semibold">Human Rating</h5>
                                      </div>
                                      <Badge variant={humanRating === "pass" ? "default" : "destructive"} className={humanRating === "pass" ? "bg-green-500 text-white" : ""}>
                                        {humanRating}
                                      </Badge>
                                      <p className="text-xs text-muted-foreground">{comparison.human_feedback?.rationale || 'No rationale provided'}</p>
                                    </div>
                                    
                                    {/* Previous Judge Version */}
                                    <div className="space-y-2">
                                      <div className="flex items-center gap-2">
                                        <Bot className="w-4 h-4" />
                                        <h5 className="text-sm font-semibold">Judge v{(judge?.version || 1) - 1}</h5>
                                      </div>
                                      <Badge variant={previousJudgeRating === "pass" ? "default" : "destructive"} className={previousJudgeRating === "pass" ? "bg-green-500 text-white" : ""}>
                                        {previousJudgeRating}
                                      </Badge>
                                      <p className="text-xs text-muted-foreground">{comparison.previous_judge_feedback?.rationale || 'No rationale provided'}</p>
                                    </div>
                                    
                                    {/* New Judge Version */}
                                    <div className="space-y-2">
                                      <div className="flex items-center gap-2">
                                        <Bot className="w-4 h-4" />
                                        <h5 className="text-sm font-semibold">Judge v{judge?.version || 1}</h5>
                                      </div>
                                      <Badge variant={newJudgeRating === "pass" ? "default" : "destructive"} className={newJudgeRating === "pass" ? "bg-green-500 text-white" : ""}>
                                        {newJudgeRating}
                                      </Badge>
                                      <p className="text-xs text-muted-foreground">{comparison.new_judge_feedback?.rationale || 'No rationale provided'}</p>
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          )
                        })}
                  </div>
                </div>
              )}
          
          {/* Navigation Button */}
          <div className="flex justify-start pt-6">
            <Button 
              onClick={() => setActiveTab("examples")} 
              variant="outline"
              className="flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Add more examples
            </Button>
          </div>
        </TabsContent>
      </Tabs>
      
      {/* Share Modal */}
      <Dialog open={shareModalOpen} onOpenChange={setShareModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Share Labeling Session</DialogTitle>
            <DialogDescription>
              Share this link with others to allow them to participate in the labeling session.
            </DialogDescription>
          </DialogHeader>
          <div className="flex items-center space-x-2">
            <div className="grid flex-1 gap-2">
              <Input
                value={shareUrl}
                readOnly
                className="h-9"
              />
            </div>
            <Button size="sm" className="px-3" onClick={copyToClipboard}>
              <Copy className="h-4 w-4" />
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Add Examples Modal */}
      <Dialog open={addExamplesModalOpen} onOpenChange={setAddExamplesModalOpen}>
        <DialogContent className="sm:max-w-4xl max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Add Examples</DialogTitle>
            <DialogDescription>
              Select traces to add as examples to this judge.
            </DialogDescription>
          </DialogHeader>
          
          {/* Instructions */}
          <div className="space-y-4 mb-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="space-y-3">
                <div className="font-medium text-blue-900">Option 1: Add from Trace UI</div>
                <ol className="list-decimal list-inside space-y-2 text-sm text-blue-800">
                  <li>
                    Open your{' '}
                    {databricksHost && judge?.experiment_id ? (
                      <button
                        onClick={() => openExperimentLink(judge.experiment_id)}
                        className="text-blue-600 underline hover:text-blue-800"
                      >
                        experiment
                      </button>
                    ) : (
                      'experiment'
                    )}{' '}
                    and select some traces
                  </li>
                  <li>Click on "Actions &gt; Add to Labeling Session"</li>
                  <li>Add to the labeling session that corresponds to your judge name</li>
                </ol>
              </div>
            </div>
            
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-3 bg-white text-gray-500 font-medium">OR</span>
              </div>
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto space-y-4">
            <div className="font-medium text-gray-900">Option 2: Add from Judge Builder</div>
            
            {tracesError && (
              <div className="text-red-600 text-sm p-3 bg-red-50 border border-red-200 rounded">
                Error loading traces: {tracesError}
              </div>
            )}
            
            {/* Select All / Deselect All */}
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Checkbox
                  checked={filteredTraces.length > 0 && selectedTraces.size === filteredTraces.length}
                  onCheckedChange={toggleSelectAll}
                />
                <label className="text-sm font-medium">
                  Select All ({filteredTraces.length} traces)
                </label>
              </div>
              <span className="text-sm text-muted-foreground">
                {selectedTraces.size} selected
              </span>
            </div>
            
            {/* Traces List */}
            <div className="border rounded-lg max-h-96 overflow-y-auto">
              {tracesLoading ? (
                <div className="text-center py-8 text-muted-foreground">
                  <div className="flex items-center justify-center gap-2">
                    <span>Loading traces</span>
                    <LoadingDots size="sm" />
                  </div>
                </div>
              ) : (
                <div className="space-y-0">
                  {filteredTraces.map((trace) => (
                    <div 
                      key={trace.trace_id} 
                      className="group flex items-start space-x-3 p-4 border-b last:border-b-0 cursor-pointer hover:bg-gray-50 transition-colors"
                      onClick={() => toggleTraceSelection(trace.trace_id)}
                      title={trace.trace_id}
                    >
                      <Checkbox
                        checked={selectedTraces.has(trace.trace_id)}
                        onCheckedChange={(checked) => {
                          // Prevent double-toggling when clicking checkbox directly
                          if (checked !== selectedTraces.has(trace.trace_id)) {
                            toggleTraceSelection(trace.trace_id)
                          }
                        }}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <div className="flex-1 min-w-0 space-y-2">
                        <div className="space-y-1">
                          <div>
                            <span className="text-xs font-semibold text-gray-600 mr-2">Request:</span>
                            <span className="text-sm">{
                              (() => {
                                try {
                                  // Try to parse if it looks like a dict string
                                  if (typeof trace.request === 'string' && trace.request.startsWith("{'")) {
                                    const jsonString = trace.request.replace(/'/g, '"')
                                    const parsed = JSON.parse(jsonString)
                                    return parsed.request || trace.request
                                  }
                                  return typeof trace.request === 'string' ? trace.request : JSON.stringify(trace.request)
                                } catch {
                                  return trace.request
                                }
                              })()
                            }</span>
                          </div>
                          <div>
                            <span className="text-xs font-semibold text-gray-600 mr-2">Response:</span>
                            <span className="text-sm text-muted-foreground">{
                              (() => {
                                try {
                                  // Try to parse if it looks like a dict string
                                  if (typeof trace.response === 'string' && trace.response.startsWith("{'")) {
                                    const jsonString = trace.response.replace(/'/g, '"')
                                    const parsed = JSON.parse(jsonString)
                                    return parsed.response || trace.response
                                  }
                                  return typeof trace.response === 'string' ? trace.response : JSON.stringify(trace.response)
                                } catch {
                                  return trace.response
                                }
                              })()
                            }</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            {!tracesLoading && filteredTraces.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                No traces found in this experiment.
              </div>
            )}
          </div>
          
          {/* Fixed footer with buttons */}
          <div className="flex justify-end gap-2 pt-4 border-t bg-white">
            <Button variant="outline" onClick={() => setAddExamplesModalOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={() => {
                addSelectedExamples()
              }}
              disabled={selectedTraces.size === 0 || addingExamples}
            >
              {addingExamples ? (
                <div className="flex items-center gap-2">
                  <LoadingDots size="sm" />
                  Adding Examples...
                </div>
              ) : (
                `Add ${selectedTraces.size} Example${selectedTraces.size !== 1 ? 's' : ''}`
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}