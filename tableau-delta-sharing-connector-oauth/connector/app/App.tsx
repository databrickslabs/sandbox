import ReactDOM from 'react-dom/client'
import React from 'react'
import 'bootstrap'
import ConnectorView from './components/ConnectorView'

const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement)
root.render(
  <React.StrictMode>
    <ConnectorView />
  </React.StrictMode>
)
