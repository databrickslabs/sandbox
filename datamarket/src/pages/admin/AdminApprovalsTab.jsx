import React from 'react'
import { AlertTriangle } from 'lucide-react'
import { useAppConfig } from '../../context/AppConfigContext'
import { DataMarketAdminPage } from '../DataMarketAdminPage'

export function AdminApprovalsTab({ onSwitchToSettings }) {
  const { sqlWarehouseId } = useAppConfig()

  return (
    <>
      {!sqlWarehouseId && (
        <div className="mb-4 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
          <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-amber-800">UC grants are disabled</p>
            <p className="text-xs text-amber-700 mt-0.5">
              Approving a request will log it in the portal but <strong>will not set any Unity Catalog permissions</strong> — the user won't actually be able to query the table.
              {' '}<button className="underline font-medium" onClick={onSwitchToSettings}>Set a SQL Warehouse ID in Settings</button> to activate real UC grants.
            </p>
          </div>
        </div>
      )}
      <DataMarketAdminPage embedded />
    </>
  )
}
