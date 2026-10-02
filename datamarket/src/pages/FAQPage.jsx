import React, { useState } from 'react'
import { ChevronDown, ChevronUp, HelpCircle } from 'lucide-react'
import { useAppConfig } from '@/context/AppConfigContext'

const DataMarket_BLUE = '#003865'

const DEFAULT_FAQ = [
  {
    q: 'What is a data product?',
    a: 'A data product is a certified, documented dataset that your organisation has made available for discovery and use. Each one has an owner, a refresh schedule, a data classification, and a governed access path.'
  },
  {
    q: 'How do I request access to a dataset?',
    a: 'Open any data product from the Discover page, then click "Request Access". Add a brief business justification and submit. A data steward will review your request — you\'ll be notified when it\'s approved or denied.'
  },
  {
    q: 'How long does approval take?',
    a: 'Approval time depends on your organisation\'s process. Once approved, your Unity Catalog permissions are granted immediately — you can query the table right away without any further steps.'
  },
  {
    q: 'What happens after my access is approved?',
    a: 'Go to My Data to see all your approved datasets. For Unity Catalog tables, you\'ll find an "Explore in UC" button that opens the table in Databricks, and a "Copy SQL" button with a ready-to-run SELECT query.'
  },
  {
    q: 'Can I search for data without knowing the exact table name?',
    a: 'Yes — use Ask AI. Type a business question or describe your use case in plain English and it will find the most relevant data products from the catalog using Databricks Foundation Models.'
  },
  {
    q: 'Who do I contact if I have a question about a specific dataset?',
    a: 'Each data product shows an owner email on its detail page. You can also reach the data team directly — see the Contact page for details.'
  },
]

function FAQItem({ item, isOpen, onToggle }) {
  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-gray-50 transition-colors"
      >
        <span className="text-sm font-medium text-gray-900 pr-4">{item.q}</span>
        {isOpen
          ? <ChevronUp className="h-4 w-4 text-gray-400 shrink-0" />
          : <ChevronDown className="h-4 w-4 text-gray-400 shrink-0" />
        }
      </button>
      {isOpen && (
        <div className="px-5 pb-4 text-sm text-gray-600 leading-relaxed border-t border-gray-100 pt-3 bg-gray-50/50">
          {item.a}
        </div>
      )}
    </div>
  )
}

export function FAQPage({ onNavigate }) {
  const { faqItems: configFaq } = useAppConfig()
  const items = configFaq?.length ? configFaq : DEFAULT_FAQ
  const [openIndex, setOpenIndex] = useState(0)

  return (
    <div className="max-w-2xl mx-auto space-y-8 py-4">

      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ backgroundColor: DataMarket_BLUE }}>
          <HelpCircle className="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Frequently Asked Questions</h1>
          <p className="text-sm text-gray-500">Common questions about using this data portal</p>
        </div>
      </div>

      <div className="space-y-2">
        {items.map((item, i) => (
          <FAQItem
            key={i}
            item={item}
            isOpen={openIndex === i}
            onToggle={() => setOpenIndex(openIndex === i ? null : i)}
          />
        ))}
      </div>

      <p className="text-sm text-gray-400 text-center">
        Didn't find what you were looking for?{' '}
        <button onClick={() => onNavigate?.('contact')}
          className="text-blue-600 hover:underline">
          Contact the data team
        </button>
      </p>

    </div>
  )
}
