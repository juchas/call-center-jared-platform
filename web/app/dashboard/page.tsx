'use client'

import { useEffect, useState } from 'react'

interface Tenant {
  id: string
  label: string | null
  status: string
  phone_number: string | null
  webhook_url: string | null
  koyeb_app_url: string | null
  created_at: string
}

const STATUS_COLORS: Record<string, string> = {
  healthy: 'bg-green-100 text-green-800',
  deploying: 'bg-yellow-100 text-yellow-800',
  provisioning: 'bg-blue-100 text-blue-800',
  error: 'bg-red-100 text-red-800',
  degraded: 'bg-orange-100 text-orange-800',
}

export default function DashboardPage() {
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    const res = await fetch('/api/tenants')
    if (res.ok) setTenants(await res.json())
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const handleDelete = async (id: string) => {
    if (!confirm('Tear down this tenant? This will release the phone number and stop billing.')) return
    await fetch(`/api/tenants/${id}`, { method: 'DELETE' })
    load()
  }

  const handleProvisionNumber = async (id: string) => {
    await fetch(`/api/tenants/${id}/provision-number`, { method: 'POST' })
    load()
  }

  if (loading) return <p className="text-sm text-gray-500">Loading…</p>

  if (!tenants.length) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500 mb-4">No tenants yet.</p>
        <a href="/" className="text-indigo-600 text-sm font-medium hover:underline">Provision your first tenant →</a>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Tenants</h1>
        <a href="/" className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
          + New tenant
        </a>
      </div>

      <div className="space-y-3">
        {tenants.map(t => (
          <div key={t.id} className="rounded-xl border bg-white p-5 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0 flex-1">

                <div className="flex items-center gap-2 mb-3">
                  <span className="font-medium">{t.label || 'Unnamed tenant'}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    STATUS_COLORS[t.status] ?? 'bg-gray-100 text-gray-700'
                  }`}>
                    {t.status}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                  {t.phone_number ? (
                    <div>
                      <p className="text-xs text-gray-400 mb-0.5">Phone number</p>
                      <p className="font-mono font-semibold text-gray-900">{t.phone_number}</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-xs text-gray-400 mb-1">Phone number</p>
                      <button
                        onClick={() => handleProvisionNumber(t.id)}
                        className="text-xs text-indigo-600 hover:underline"
                      >
                        Provision number →
                      </button>
                    </div>
                  )}

                  <div>
                    <p className="text-xs text-gray-400 mb-0.5">Webhook URL</p>
                    {t.webhook_url
                      ? <code className="text-xs text-gray-600 break-all">{t.webhook_url}</code>
                      : <p className="text-xs text-gray-400">Pending…</p>
                    }
                  </div>
                </div>

                <p className="text-xs text-gray-300 mt-3">ID: {t.id}</p>
              </div>

              <button
                onClick={() => handleDelete(t.id)}
                className="shrink-0 text-xs text-red-400 hover:text-red-600"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
