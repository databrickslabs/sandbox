import './Spinner.css'

interface SpinnerProps {
  size?: 'small' | 'medium' | 'large'
}

export default function Spinner({ size = 'medium' }: SpinnerProps) {
  return <div className={`spinner spinner-${size}`}></div>
}
