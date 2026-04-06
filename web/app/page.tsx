'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

interface FormState {
  label: string
  openai_key: string
  sn_instance: string
  sn_user: string
  sn_pass: string
}

export default function SignupPage() {
  const router = useRouter()
  const [form, setForm] = useState<FormState>({
    label: '',
    openai_key: '',
    sn_instance: '',
    sn_user: '',
    sn_pass: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<{ webhook_url: string; id: string } | null>(null)

  const handleSubmit = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/tenants', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Provisioning failed')
      }
      const data = await res.json()
      setResult(data)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const set = (k: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }))

  if (result) {
    return (
      <div className="rounded-xl border bg-white p-8 shadow-sm max-w-lg">
        <h2 className="text-lg font-semibold mb-4">Tenant provisioned</h2>
        <p className="text-sm text-gray-600 mb-2">Your Twilio webhook URL:</p>
        <code className="block bg-gray-100 rounded p-3 text-sm break-all mb-6">
          {result.webhook_url ?? 'Deploying… check dashboard in ~30s'}
        </code>
        <p className="text-xs text-gray-500 mb-4">
          Point your Twilio phone number's Voice webhook to this URL (HTTP POST).
        </p>
        <button
          onClick={() => router.push('/dashboard')}
          className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Go to dashboard
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-semibold mb-2">New tenant</h1>
      <p className="text-sm text-gray-500 mb-8">
        Provide your credentials. Each tenant gets a dedicated container on Koyeb with its own Twilio webhook URL.
      </p>

      <div className="space-y-4">
        <Field label="Label (optional)" type="text" value={form.label} onChange={set('label')} placeholder="Acme Corp" />

        <div className="border-t pt-4">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-3">OpenAI</p>
          <Field label="API key" type="password" value={form.openai_key} onChange={set('openai_key')} placeholder="sk-proj-..." required />
        </div>

        <div className="border-t pt-4">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-3">ServiceNow</p>
          <Field label="Instance name" type="text" value={form.sn_instance} onChange={set('sn_instance')} placeholder="myinstance" required />
          <Field label="Username" type="text" value={form.sn_user} onChange={set('sn_user')} placeholder="admin" required />
          <Field label="Password" type="password" value={form.sn_pass} onChange={set('sn_pass')} placeholder="••••••" required />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          onClick={handleSubmit}
          disabled={loading || !form.openai_key || !form.sn_instance || !form.sn_user || !form.sn_pass}
          className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Provisioning…' : 'Provision tenant'}
        </button>
      </div>
    </div>
  )
}

function Field({
  label, type, value, onChange, placeholder, required,
}: {
  label: string
  type: string
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  placeholder?: string
  required?: boolean
}) {
  return (
    <div className="mb-3">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
      />
    </div>
  )
}
