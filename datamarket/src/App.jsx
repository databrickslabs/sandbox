import React, { useState } from 'react'
import { PersonaProvider } from './context/PersonaContext'
import { AppConfigProvider } from './context/AppConfigContext'
import { DataMarketLayout } from './components/layout/DataMarketLayout'
import { FirstRunWizard } from './components/FirstRunWizard'
import { DataMarketHomePage } from './pages/DataMarketHomePage'
import { DataMarketCatalogPage } from './pages/DataMarketCatalogPage'
import { DataMarketProductDetailPage } from './pages/DataMarketProductDetailPage'
import { DataMarketLibraryPage } from './pages/DataMarketLibraryPage'
import { DataMarketRegisterPage } from './pages/DataMarketRegisterPage'
import { DataMarketInsightsPage } from './pages/DataMarketInsightsPage'
import { AIExplorerPage } from './pages/AIExplorerPage'
import { AboutPage } from './pages/AboutPage'
import { FAQPage } from './pages/FAQPage'
import { ContactPage } from './pages/ContactPage'
import { FeatureRequestPage } from './pages/FeatureRequestPage'
import { useAppConfig } from './context/AppConfigContext'
import { usePersona } from './context/PersonaContext'

function AppInner() {
  const [currentPage, setCurrentPage] = useState('home')
  const [pageProps, setPageProps] = useState({})
  const [selectedProduct, setSelectedProduct] = useState(null)
  const [wizardDismissed, setWizardDismissed] = useState(false)

  const { setupComplete } = useAppConfig()
  const { isAdmin } = usePersona()

  const showWizard = !setupComplete && isAdmin && !wizardDismissed

  const navigate = (page, props = {}) => {
    setCurrentPage(page)
    setPageProps(props)
    setSelectedProduct(null)
    window.scrollTo(0, 0)
  }

  const openProduct = (product) => {
    setSelectedProduct(product)
    setCurrentPage('detail')
    window.scrollTo(0, 0)
  }

  const renderPage = () => {
    if (currentPage === 'detail' && selectedProduct) {
      return <DataMarketProductDetailPage product={selectedProduct} onBack={() => navigate('discover')} onNavigate={navigate} />
    }
    switch (currentPage) {
      case 'home':         return <DataMarketHomePage onNavigate={navigate} onOpenProduct={openProduct} />
      // Discover (catalog)
      case 'discover':
      case 'data':
      case 'catalog':      return <DataMarketCatalogPage onOpenProduct={openProduct} initialSearch={pageProps.search || ''} onNavigate={navigate} />
      // Ask AI (FMAPI)
      case 'ask-ai':
      case 'ai-explorer':  return <AIExplorerPage initialQuestion={pageProps.question || ''} onNavigate={navigate} onOpenProduct={openProduct} />
      // Insights (dashboard gallery)
      case 'insights':     return <DataMarketInsightsPage onNavigate={navigate} onOpenProduct={openProduct} />
      // My Data / Manage — unified for both regular users and admin
      case 'my-access':
      case 'library':
      case 'my-library':   return <DataMarketLibraryPage onNavigate={navigate} onOpenProduct={openProduct} />
      case 'admin':        return <DataMarketLibraryPage onNavigate={navigate} onOpenProduct={openProduct} initialTab="Manage Approvals" />
      case 'register':     return <DataMarketRegisterPage onNavigate={navigate} editProduct={pageProps.editProduct || null} />
      case 'about':           return <AboutPage onNavigate={navigate} />
      case 'faq':             return <FAQPage onNavigate={navigate} />
      case 'contact':         return <ContactPage onNavigate={navigate} />
      case 'feature-requests': return <FeatureRequestPage onNavigate={navigate} />
      default:             return <DataMarketHomePage onNavigate={navigate} onOpenProduct={openProduct} />
    }
  }

  return (
    <DataMarketLayout currentPage={currentPage} onNavigate={navigate}>
      {renderPage()}
      {showWizard && <FirstRunWizard onDismiss={() => setWizardDismissed(true)} />}
    </DataMarketLayout>
  )
}

function App() {
  return (
    <AppConfigProvider>
      <PersonaProvider>
        <AppInner />
      </PersonaProvider>
    </AppConfigProvider>
  )
}

export default App
