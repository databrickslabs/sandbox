import { ReactNode } from 'react'
import './ThreePanel.css'

interface ThreePanelProps {
  left: ReactNode
  center: ReactNode
  right: ReactNode
}

export default function ThreePanel({ left, center, right }: ThreePanelProps) {
  return (
    <div className="three-panel">
      <aside className="panel-left">{left}</aside>
      <main className="panel-center">{center}</main>
      <aside className="panel-right">{right}</aside>
    </div>
  )
}
