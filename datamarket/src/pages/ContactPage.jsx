import React from 'react'
import { Mail, MessageSquare, HelpCircle, ExternalLink } from 'lucide-react'
import { useAppConfig } from '@/context/AppConfigContext'

const DataMarket_BLUE = '#003865'

export function ContactPage({ onNavigate }) {
  const { appName, contactName, contactEmail, contactNote } = useAppConfig()

  const name  = contactName  || 'Your Data Team'
  const email = contactEmail || ''

  return (
    <div className="max-w-xl mx-auto space-y-8 py-4">

      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ backgroundColor: DataMarket_BLUE }}>
          <MessageSquare className="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Contact</h1>
          <p className="text-sm text-gray-500">Get in touch with the {appName} team</p>
        </div>
      </div>

      {/* Contact card */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-full flex items-center justify-center text-white font-semibold text-lg shrink-0"
            style={{ backgroundColor: DataMarket_BLUE }}>
            {name.charAt(0).toUpperCase()}
          </div>
          <div>
            <p className="font-semibold text-gray-900">{name}</p>
            <p className="text-xs text-gray-400 mt-0.5">{appName} administrator</p>
          </div>
        </div>

        {email && (
          <a href={`mailto:${email}`}
            className="flex items-center gap-3 px-4 py-3 rounded-xl border border-gray-100 bg-gray-50 hover:bg-blue-50 hover:border-blue-200 transition-colors group">
            <Mail className="h-4 w-4 text-gray-400 group-hover:text-blue-600 shrink-0" />
            <span className="text-sm text-gray-700 group-hover:text-blue-700">{email}</span>
            <ExternalLink className="h-3 w-3 text-gray-300 group-hover:text-blue-400 ml-auto" />
          </a>
        )}

        {contactNote && (
          <p className="text-sm text-gray-500 leading-relaxed border-t border-gray-100 pt-4">
            {contactNote}
          </p>
        )}

        {!email && !contactNote && (
          <p className="text-sm text-gray-400 italic">
            Contact details not yet configured. An admin can set them under Manage → Settings.
          </p>
        )}
      </div>

      {/* Quick links */}
      <div className="space-y-2">
        <p className="text-xs text-gray-400 uppercase tracking-wide font-semibold">Quick links</p>
        <button onClick={() => onNavigate?.('faq')}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-xl border border-gray-100 hover:bg-gray-50 transition-colors text-left">
          <HelpCircle className="h-4 w-4 text-gray-400 shrink-0" />
          <div>
            <p className="text-sm font-medium text-gray-700">Browse the FAQ</p>
            <p className="text-xs text-gray-400">Answers to common questions about the portal</p>
          </div>
        </button>
        <button onClick={() => onNavigate?.('discover')}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-xl border border-gray-100 hover:bg-gray-50 transition-colors text-left">
          <Mail className="h-4 w-4 text-gray-400 shrink-0" />
          <div>
            <p className="text-sm font-medium text-gray-700">Browse data products</p>
            <p className="text-xs text-gray-400">Discover what data is available in your catalog</p>
          </div>
        </button>
      </div>

    </div>
  )
}
