import { useRef, useState, useEffect } from "react"
import { TemplateVariableButtons } from "./TemplateVariableButtons"
import { validateTemplateVariables } from "@/lib/templateValidation"
import { AlertCircle, CheckCircle } from "lucide-react"

interface JudgeInstructionInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
  required?: boolean
  showValidation?: boolean
}

export function JudgeInstructionInput({
  value,
  onChange,
  placeholder = "Enter evaluation criteria and instructions",
  disabled = false,
  required = false,
  showValidation = true
}: JudgeInstructionInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [validation, setValidation] = useState<{
    isValid: boolean
    error?: string
    suggestions?: string[]
  }>({ isValid: true })

  // Validate on value change with debouncing
  useEffect(() => {
    if (!showValidation) {
      setValidation({ isValid: true })
      return
    }

    const timeoutId = setTimeout(() => {
      if (value.trim()) {
        const result = validateTemplateVariables(value)
        setValidation(result)
      } else {
        setValidation({ isValid: true })
      }
    }, 300) // 300ms debounce for better performance

    return () => clearTimeout(timeoutId)
  }, [value, showValidation])

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value)
  }

  const handleVariableInsert = (variable: string) => {
    // Validation will be updated automatically via useEffect
  }

  const hasError = showValidation && !validation.isValid && value.trim()
  const hasSuccess = showValidation && validation.isValid && value.trim()

  return (
    <div className="space-y-4">
      {/* Main Textarea */}
      <div className="space-y-2">
        <label className="block text-sm font-medium">
          Evaluation Instruction {required && <span className="text-red-500">*</span>}
        </label>
        
        {/* Output Types Guidance - Below title */}
        <p className="text-xs text-muted-foreground">
          <strong>Ensure you define your expected output types!</strong> For example, "return pass or fail", or "return good, bad, or not applicable".
        </p>
        
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleChange}
            className={`w-full min-h-[120px] px-3 py-2 border rounded-md text-sm resize-none focus:outline-none focus:ring-2 transition-colors ${
              hasError 
                ? 'border-red-300 focus:ring-red-500 focus:border-red-500' 
                : hasSuccess
                ? 'border-green-300 focus:ring-green-500 focus:border-green-500'
                : 'border-input bg-background focus:ring-ring focus:border-ring'
            }`}
            placeholder={placeholder}
            disabled={disabled}
          />
          
          {/* Status Icons */}
          {showValidation && value.trim() && (
            <div className="absolute top-2 right-2">
              {hasError ? (
                <AlertCircle className="w-4 h-4 text-red-500" />
              ) : hasSuccess ? (
                <CheckCircle className="w-4 h-4 text-green-500" />
              ) : null}
            </div>
          )}
        </div>

        {/* Validation Messages */}
        {showValidation && hasError && (
          <div className="space-y-2">
            <p className="text-sm text-red-600 flex items-center gap-1">
              <AlertCircle className="w-3 h-3" />
              {validation.error}
            </p>
            {validation.suggestions && (
              <div className="bg-red-50 border border-red-200 rounded p-3">
                <p className="text-xs font-medium text-red-700 mb-1">Suggestions:</p>
                <ul className="text-xs text-red-600 space-y-1">
                  {validation.suggestions.map((suggestion, index) => (
                    <li key={index} className="flex items-start gap-1">
                      <span className="text-red-400 mt-0.5">•</span>
                      <span>{suggestion}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Success Message */}
        {showValidation && hasSuccess && (
          <p className="text-sm text-green-600 flex items-center gap-1">
            <CheckCircle className="w-3 h-3" />
            Instructions contain valid template variables
          </p>
        )}

      </div>

      {/* Template Variable Buttons - Below textarea */}
      <TemplateVariableButtons 
        textareaRef={textareaRef}
        onInsert={handleVariableInsert}
        disabled={disabled}
      />
    </div>
  )
}