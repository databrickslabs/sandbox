import { useState, useEffect, useCallback } from 'react'
import { JudgeBuildersService, JudgesService, LabelingService, ExperimentsService, AlignmentService } from '@/fastapi_client'
import type { JudgeResponse, ExamplesResponse, LabelingProgress } from '@/fastapi_client'

// Hook for fetching judge details
export function useJudge(judgeId: string | undefined) {
  const [judge, setJudge] = useState<JudgeResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!judgeId) {
      setLoading(false)
      return
    }

    const fetchJudge = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await JudgeBuildersService.getJudgeBuilderApiJudgeBuildersJudgeIdGet(judgeId)
        setJudge(response)
      } catch (err) {
        console.error('Error fetching judge:', err)
        setError(err instanceof Error ? err.message : 'Failed to fetch judge')
      } finally {
        setLoading(false)
      }
    }

    fetchJudge()
  }, [judgeId])

  return { judge, loading, error, refetch: () => {
    if (judgeId) {
      JudgeBuildersService.getJudgeBuilderApiJudgeBuildersJudgeIdGet(judgeId).then(setJudge).catch(console.error)
    }
  }}
}

// Hook for fetching judge examples
export function useJudgeExamples(judgeId: string | undefined, includeJudgeResults: boolean = false) {
  const [examples, setExamples] = useState<ExamplesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!judgeId) {
      setLoading(false)
      return
    }

    const fetchExamples = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await LabelingService.getExamplesApiLabelingJudgeIdExamplesGet(judgeId, includeJudgeResults)
        setExamples(response)
      } catch (err) {
        console.error('Error fetching examples:', err)
        setError(err instanceof Error ? err.message : 'Failed to fetch examples')
      } finally {
        setLoading(false)
      }
    }

    fetchExamples()
  }, [judgeId, includeJudgeResults])

  return { examples, loading, error, refetch: () => {
    if (judgeId) {
      setLoading(true)
      setError(null)
      LabelingService.getExamplesApiLabelingJudgeIdExamplesGet(judgeId, includeJudgeResults)
        .then(setExamples)
        .catch(err => {
          console.error(err)
          setError(err instanceof Error ? err.message : 'Failed to fetch examples')
        })
        .finally(() => setLoading(false))
    }
  }}
}

// Hook for fetching labeling progress
export function useLabelingProgress(judgeId: string | undefined) {
  const [progress, setProgress] = useState<LabelingProgress | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!judgeId) {
      setLoading(false)
      return
    }

    const fetchProgress = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await LabelingService.getLabelingProgressApiLabelingJudgeIdLabelingProgressGet(judgeId)
        setProgress(response)
      } catch (err) {
        console.error('Error fetching labeling progress:', err)
        setError(err instanceof Error ? err.message : 'Failed to fetch labeling progress')
      } finally {
        setLoading(false)
      }
    }

    fetchProgress()
  }, [judgeId])

  return { progress, loading, error, refetch: () => {
    if (judgeId) {
      setLoading(true)
      setError(null)
      LabelingService.getLabelingProgressApiLabelingJudgeIdLabelingProgressGet(judgeId)
        .then(setProgress)
        .catch(err => {
          console.error(err)
          setError(err instanceof Error ? err.message : 'Failed to fetch labeling progress')
        })
        .finally(() => setLoading(false))
    }
  }}
}

// Hook for running alignment
export function useAlignment() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [needsRefresh, setNeedsRefresh] = useState(false)

  const runAlignment = async (judgeId: string, experimentId: string) => {
    try {
      setLoading(true)
      setError(null)
      setNeedsRefresh(false)

      // Start alignment in background
      const response = await AlignmentService.runAlignmentApiAlignmentJudgeIdAlignPost(judgeId)
      console.log('[Alignment] Started background alignment:', response)

      // Wait a bit before first poll to let background task start
      await new Promise(resolve => setTimeout(resolve, 1000))

      // Poll for completion using exponential backoff
      const pollForCompletion = async (attempt: number = 0, maxRetries: number = 20): Promise<any> => {
        if (attempt >= maxRetries) {
          throw new Error('Alignment polling timed out after maximum attempts')
        }

        try {
          // Check alignment status
          const statusResponse = await AlignmentService.getAlignmentStatusApiAlignmentJudgeIdAlignStatusGet(judgeId)
          console.log(`[Alignment Poll ${attempt + 1}] Status:`, statusResponse)

          if (statusResponse.status === 'completed') {
            return statusResponse.result
          } else if (statusResponse.status === 'running') {
            // Still running, wait and retry
            // Exponential backoff with cap: 2s, 4s, 8s, 16s, 30s, 30s, ...
            const delay = Math.min(Math.pow(2, attempt) * 2000, 30000)
            console.log(`[Alignment Poll ${attempt + 1}] Still running, waiting ${delay}ms before next poll`)
            await new Promise(resolve => setTimeout(resolve, delay))
            return pollForCompletion(attempt + 1, maxRetries)
          } else {
            // Should not happen, but handle gracefully
            throw new Error(`Unexpected status: ${statusResponse.status}`)
          }
        } catch (pollErr) {
          // If we get an error from the status endpoint, it means alignment failed
          // The status endpoint will throw an HTTPException with the appropriate error
          console.error('[Alignment Poll] Error:', pollErr)
          throw pollErr
        }
      }

      // Wait for alignment to complete
      const result = await pollForCompletion()
      console.log('[Alignment] Completed successfully:', result)
      return result

    } catch (err) {
      console.error('Error running alignment:', err)

      // Check if this is an insufficient examples error
      const errorMessage = err instanceof Error ? err.message : String(err)
      const errorString = JSON.stringify(err)
      const isInsufficientExamples = (
        errorMessage.includes('Insufficient labeled examples') ||
        errorMessage.includes('need at least') ||
        errorString.includes('Insufficient labeled examples') ||
        errorString.includes('need at least')
      )

      if (isInsufficientExamples) {
        setError('insufficient_examples')
        throw err
      }

      // Check if this is a 422 optimization failure error
      const isOptimizationFailure = err instanceof Error && (
        err.message.includes('422') ||
        err.message.includes('Judge optimization failed')
      )

      if (isOptimizationFailure) {
        setError('Judge optimization failed. Please check the app logs for details.')
        throw err
      }

      // Check if this is a 409 already running error
      const isAlreadyRunning = err instanceof Error && err.message.includes('409')

      if (isAlreadyRunning) {
        setError('Alignment is already running for this judge')
        throw err
      }

      setError(err instanceof Error ? err.message : 'Failed to run alignment')
      throw err
    } finally {
      setLoading(false)
    }
  }

  const checkAlignmentStatus = async (judgeId: string) => {
    try {
      setLoading(true)
      setError(null)
      setNeedsRefresh(false)
      const response = await AlignmentService.getAlignmentComparisonApiAlignmentJudgeIdAlignmentComparisonGet(judgeId)
      return response
    } catch (err) {
      console.error('Error checking alignment status:', err)
      setError(err instanceof Error ? err.message : 'Failed to check alignment status')
      throw err
    } finally {
      setLoading(false)
    }
  }

  return { runAlignment, checkAlignmentStatus, loading, error, needsRefresh }
}

// Hook for fetching alignment comparison data
export function useAlignmentComparison(judgeId: string | undefined) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const [hasFetched, setHasFetched] = useState(false)

  const fetchComparison = useCallback(async (maxRetries = 5) => {
    try {
      if (!judgeId) {
        return null
      }

      setHasFetched(true)
      setLoading(true)
      setError(null)
      
      const attemptFetch = async (attempt: number): Promise<any> => {
        try {
          const response = await AlignmentService.getAlignmentComparisonApiAlignmentJudgeIdAlignmentComparisonGet(judgeId)
          setData(response)
          setRetryCount(0) // Reset retry count on success
          setLoading(false)
          return response
        } catch (err) {
          if (attempt < maxRetries - 1) {
            // Wait before retrying (exponential backoff: 1s, 2s, 4s, 8s, 16s)
            const delay = Math.pow(2, attempt) * 1000
            await new Promise(resolve => setTimeout(resolve, delay))
            setRetryCount(attempt + 1)
            return attemptFetch(attempt + 1)
          } else {
            // Max retries reached - handle gracefully without throwing
            const errorMessage = err instanceof Error ? err.message : 'Failed to fetch alignment comparison'
            setError(`Failed to load alignment data after ${maxRetries} attempts: ${errorMessage}`)
            setRetryCount(maxRetries)
            setLoading(false)
            // Don't throw to prevent white page crash
            return null
          }
        }
      }

      return await attemptFetch(0)
    } catch (outerError) {
      // Outermost safety net for any errors
      setError(`Error: ${outerError instanceof Error ? outerError.message : String(outerError)}`)
      setLoading(false)
      return null
    }
  }, [])

  const resetData = useCallback(() => {
    setData(null)
    setError(null)
    setHasFetched(false)
    setRetryCount(0)
  }, [judgeId])

  return { data, loading, error, fetchComparison, resetData, retryCount, hasFetched }
}

// Hook for fetching experiment traces
export function useExperimentTraces(experimentId: string | undefined, runId?: string) {
  const [traces, setTraces] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!experimentId) {
      setLoading(false)
      return
    }

    const fetchTraces = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await ExperimentsService.getExperimentTracesApiExperimentsExperimentIdTracesGet(experimentId, runId)
        setTraces(response.traces || [])
      } catch (err) {
        console.error('Error fetching traces:', err)
        setError(err instanceof Error ? err.message : 'Failed to fetch traces')
      } finally {
        setLoading(false)
      }
    }

    fetchTraces()
  }, [experimentId, runId])

  return { traces, loading, error, refetch: () => {
    if (experimentId) {
      ExperimentsService.getExperimentTracesApiExperimentsExperimentIdTracesGet(experimentId, runId)
        .then(response => setTraces(response.traces || []))
        .catch(console.error)
    }
  }}
}