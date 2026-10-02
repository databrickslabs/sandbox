import { createContext, useContext, useEffect, useState, useCallback } from 'react'

const defaults = {
  appName:       'DataMarket',
  appSubtitle:   'Data Discovery & Access',
  appLogoUrl:    '',
  demoMode:      true,
  sqlWarehouseId:'',
  rfaEnabled:    false,
  setupComplete: false,
  autoDiscoverEnabled: false,
  autoDiscoverPrefix:  '',
  databricksHost: '',
  askAiEnabled:           true,
  insightsEnabled:        true,
  featureRequestsEnabled: false,
  contributeUrl:          '',
  searchChips:     [],
  navLinks: [
    { label: 'About',   visible: true },
    { label: 'FAQ',     visible: true },
    { label: 'Contact', visible: true },
  ],
  aboutText:    '',
  contactName:  '',
  contactEmail: '',
  contactNote:  '',
  faqItems:     [],
}

const AppConfigContext = createContext({ ...defaults, refreshConfig: () => {} })

export function AppConfigProvider({ children }) {
  const [config, setConfig] = useState(defaults)

  const refreshConfig = useCallback(() => {
    fetch('/api/portal/config')
      .then(r => r.json())
      .then(data => setConfig({ ...defaults, ...data }))
      .catch(() => { /* keep defaults */ })
  }, [])

  useEffect(() => { refreshConfig() }, [refreshConfig])

  return (
    <AppConfigContext.Provider value={{ ...config, refreshConfig }}>
      {children}
    </AppConfigContext.Provider>
  )
}

export function useAppConfig() {
  return useContext(AppConfigContext)
}
