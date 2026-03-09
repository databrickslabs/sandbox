import { SuggestedQuestion } from '../../utils/suggestedQuestions'
import './SuggestedQuestions.css'

interface SuggestedQuestionsProps {
  questions: SuggestedQuestion[]
  onAskQuestion: (question: string) => void
}

export default function SuggestedQuestions({ questions, onAskQuestion }: SuggestedQuestionsProps) {
  if (questions.length === 0) return null

  return (
    <div className="suggested-questions">
      <div className="suggested-questions-divider" />
      <h4 className="suggested-questions-title">Ask AI about this asset</h4>
      <div className="suggested-questions-list">
        {questions.map((q, i) => (
          <button
            key={i}
            className="suggested-question-row"
            onClick={() => onAskQuestion(q.text)}
          >
            <span className="suggested-question-icon">?</span>
            <span className="suggested-question-text">{q.text}</span>
            <span className="suggested-question-arrow">&rarr;</span>
          </button>
        ))}
      </div>
    </div>
  )
}
