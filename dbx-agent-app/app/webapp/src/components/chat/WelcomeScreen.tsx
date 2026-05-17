import { getWelcomeQuestions } from '../../utils/suggestedQuestions'
import './WelcomeScreen.css'

interface WelcomeScreenProps {
  onSelectQuestion: (question: string) => void
}

const CATEGORY_ICONS: Record<string, string> = {
  search: '\u{1F50D}',
  link: '\u{1F517}',
  alert: '\u{26A0}\u{FE0F}',
  code: '\u{1F4BB}',
}

export default function WelcomeScreen({ onSelectQuestion }: WelcomeScreenProps) {
  const categories = getWelcomeQuestions()

  return (
    <div className="welcome-screen">
      <h3 className="welcome-heading">What would you like to explore?</h3>
      <p className="welcome-subheading">
        Ask questions about your data assets, relationships, and more
      </p>
      <div className="welcome-categories">
        {categories.map((category) => (
          <div key={category.title} className="welcome-category">
            <div className="welcome-category-header">
              <span className="welcome-category-icon">
                {CATEGORY_ICONS[category.icon] || ''}
              </span>
              <h4 className="welcome-category-title">{category.title}</h4>
            </div>
            <div className="welcome-questions">
              {category.questions.map((q, i) => (
                <button
                  key={i}
                  className="welcome-question-chip"
                  onClick={() => onSelectQuestion(q.text)}
                >
                  {q.text}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
