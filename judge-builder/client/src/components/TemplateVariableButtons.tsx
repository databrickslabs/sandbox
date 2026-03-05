import { Button } from "@/components/ui/button"
import { TEMPLATE_VARIABLES, getTemplateVariableDescription } from "@/lib/templateValidation"
import { RefObject } from "react"

interface TemplateVariableButtonsProps {
  textareaRef: RefObject<HTMLTextAreaElement>
  onInsert?: (variable: string) => void
  disabled?: boolean
}

export function TemplateVariableButtons({ 
  textareaRef, 
  onInsert, 
  disabled = false 
}: TemplateVariableButtonsProps) {
  
  const insertVariable = (variable: string) => {
    if (!textareaRef.current) {
      console.warn('Textarea ref not available for variable insertion')
      return
    }
    
    try {
      const textarea = textareaRef.current
      const start = textarea.selectionStart ?? 0
      const end = textarea.selectionEnd ?? 0
      const text = textarea.value
      
      // Insert the variable at cursor position
      const newText = text.substring(0, start) + variable + text.substring(end)
      
      // Update the value
      textarea.value = newText
      
      // Trigger change event for React
      const event = new Event('input', { bubbles: true })
      textarea.dispatchEvent(event)
      
      // Move cursor to end of inserted variable
      const newCursorPos = start + variable.length
      textarea.focus()
      textarea.setSelectionRange(newCursorPos, newCursorPos)
      
      // Call optional callback
      onInsert?.(variable)
    } catch (error) {
      console.error('Failed to insert template variable:', error)
      // Still call callback for state consistency
      onInsert?.(variable)
    }
  }

  const templateVariableButtons = [
    {
      variable: TEMPLATE_VARIABLES.INPUTS,
      label: 'inputs',
      color: 'bg-blue-100 hover:bg-blue-200 text-blue-700 border-blue-300'
    },
    {
      variable: TEMPLATE_VARIABLES.OUTPUTS,  
      label: 'outputs',
      color: 'bg-green-100 hover:bg-green-200 text-green-700 border-green-300'
    },
    {
      variable: TEMPLATE_VARIABLES.EXPECTATIONS,
      label: 'expectations', 
      color: 'bg-purple-100 hover:bg-purple-200 text-purple-700 border-purple-300'
    },
    {
      variable: TEMPLATE_VARIABLES.TRACE,
      label: 'trace',
      color: 'bg-orange-100 hover:bg-orange-200 text-orange-700 border-orange-300'  
    }
  ]

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {templateVariableButtons.map(({ variable, label, color }) => (
          <Button
            key={variable}
            type="button"
            variant="outline"
            size="sm"
            disabled={disabled}
            onClick={() => insertVariable(variable)}
            className={`text-xs font-mono ${color} ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            title={`Insert ${variable} - ${getTemplateVariableDescription(variable)}`}
            aria-label={`Insert ${variable} template variable`}
          >
            {label}
          </Button>
        ))}
      </div>
      
      <p className="text-xs text-muted-foreground">
        Click on the variables above to reference data in your judge instructions. 
        At least one variable is required.
      </p>
    </div>
  )
}