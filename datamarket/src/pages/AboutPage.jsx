import React from 'react'
import { Database, ShieldCheck, Users, Zap, ArrowRight, ExternalLink, MessageSquarePlus } from 'lucide-react'
import { useAppConfig } from '@/context/AppConfigContext'

const DataMarket_BLUE = '#003865'

const FEATURES = [
  { icon: Database,    title: 'Unified data catalog',  desc: 'Browse and search all certified data products across your organization in one place.' },
  { icon: ShieldCheck, title: 'Governed access',        desc: 'Request access to datasets. Stewards review and approve — Unity Catalog permissions are set automatically.' },
  { icon: Users,       title: 'Role-based experience',  desc: 'Analysts discover and request. Managers review team usage. Stewards publish and approve. Admins configure everything.' },
  { icon: Zap,         title: 'AI-powered discovery',   desc: 'Describe what you need in plain English. Databricks Foundation Models find the most relevant data products instantly.' },
]

export function AboutPage({ onNavigate }) {
  const { appName, appSubtitle, appLogoUrl, aboutText, contributeUrl } = useAppConfig()

  return (
    <div className="max-w-3xl mx-auto space-y-10 py-4">

      {/* Hero */}
      <div className="flex items-start gap-5">
        {appLogoUrl
          ? <img src={appLogoUrl} alt={appName} className="w-16 h-16 rounded-2xl ring-2 ring-gray-100 shrink-0" />
          : (
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center shrink-0" style={{ backgroundColor: DataMarket_BLUE }}>
              <Database className="h-8 w-8 text-white" />
            </div>
          )
        }
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{appName}</h1>
          <p className="text-gray-500 mt-1">{appSubtitle}</p>
          <span className="inline-flex items-center gap-1.5 mt-3 text-xs px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 font-medium border border-blue-100">
            Powered by Databricks
          </span>
        </div>
      </div>

      {/* About text — admin-configured or sensible default */}
      <div className="prose prose-sm max-w-none text-gray-600 leading-relaxed bg-white rounded-xl border border-gray-100 p-6">
        {aboutText
          ? aboutText.split('\n').map((line, i) => <p key={i}>{line}</p>)
          : (
            <>
              <p>
                <strong className="text-gray-900">{appName}</strong> is a self-service data portal built on Databricks.
                It gives every team in the organisation a single place to discover what data exists, understand what it means,
                and request access — without filing a ticket or waiting for an engineer.
              </p>
              <p>
                All data products listed here are certified and managed by your data stewards.
                Access is governed through Unity Catalog: when a steward approves your request,
                permissions are granted automatically and you can query the table immediately.
              </p>
              <p>
                Use the <strong>Discover</strong> tab to browse the catalog, <strong>Ask AI</strong> to search
                in plain English, and <strong>My Data</strong> to track your requests and approved datasets.
              </p>
            </>
          )
        }
      </div>

      {/* Feature grid */}
      <div>
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-4">What you can do</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {FEATURES.map(f => (
            <div key={f.title} className="bg-white rounded-xl border border-gray-100 p-4 flex gap-3">
              <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 bg-blue-50">
                <f.icon className="h-4.5 w-4.5 text-blue-600" style={{ width: 18, height: 18 }} />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-800">{f.title}</p>
                <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* CTA */}
      <div className="flex flex-wrap gap-3">
        <button onClick={() => onNavigate?.('discover')}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white"
          style={{ backgroundColor: DataMarket_BLUE }}>
          Browse the catalog <ArrowRight className="h-4 w-4" />
        </button>
        <button onClick={() => onNavigate?.('ask-ai')}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium border border-gray-200 text-gray-700 hover:bg-gray-50">
          Try Ask AI
        </button>
        {contributeUrl && (
          <a href={contributeUrl} target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium border border-orange-200 text-orange-700 bg-orange-50 hover:bg-orange-100">
            <MessageSquarePlus className="h-4 w-4" />
            Suggest a feature
            <ExternalLink className="h-3 w-3 opacity-60" />
          </a>
        )}
      </div>

    </div>
  )
}
