import { useState, useEffect, useRef } from 'react'
import './SearchBox.css'

interface SearchBoxProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

export default function SearchBox({ value, onChange, placeholder = 'Search...' }: SearchBoxProps) {
  const [localValue, setLocalValue] = useState(value)
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  useEffect(() => {
    const timeout = setTimeout(() => {
      onChangeRef.current(localValue)
    }, 300)

    return () => clearTimeout(timeout)
  }, [localValue])

  return (
    <div className="search-box">
      <input
        type="text"
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        placeholder={placeholder}
        className="search-input"
      />
      {localValue && (
        <button
          className="search-clear"
          onClick={() => setLocalValue('')}
          aria-label="Clear search"
        >
          ×
        </button>
      )}
    </div>
  )
}
