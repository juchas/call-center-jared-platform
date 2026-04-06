'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

interface FormState {
  label: string
  openai_key: string
  sn_instance: string
  sn_user: string
  sn_pass: string
  twilio_sid: string
  twilio_token: string
  phone_country: string
}

const COUNTRIES = [
  { code: 'US', label: 'United States (+1)' },
  { code: 'GB', label: 'United Kingdom (+44)' },
  { code: 'DE', label: 'Germany (+49)' },
  { code: 'PL', label: 'Poland (+48)' },
  { code: 'FR', label: 'France (+33)' },
  { code: 'NL', label: 'Netherlands (+31)' },
  { code: 'CH', label: 'Switzerland (+41)' },
  { code: 'AT', label: 'Austria (+43)' },
]

export default function SignupPage() {
  const router = useRouter()
  const [form, setForm] = useState<FormState>({
    label: '',
    openai_key: '',
    sn_instance: '',
    sn_user: '',
    sn_pass: '',
    twilio_sid: '',
    twilio_token: '',
    phone_country: 'US',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<{ phone_number: string | null; webhook_url: string | null; id: string } | null>(null)

  const handleSubmit = async () => {
    setLoading(true)
    setError(null)
    try {
      const payload: Record<string, string | null> = { ...form }
      if (!form.twilio_sid) { payload.twilio_sid = null; payload.twilio_token = null }
      const res = await fetch('/api/tenants', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error((await res.json()).detail || 'Provisioning failed')
      setResult(await res.json())
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const set = (k: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }))

  if (result) {
    return (
      <div className="rounded-xl border bg-white p-8 shadow-sm max-w-lg">
        <h2 className="text-lg font-semibold mb-4">Tenant provisioned</h2>

        {result.phone_number ? (
          <>
            <p className="text-sm text-gray-500 mb-1">Your phone number</p>
            <p className="text-2xl font-mono font-semibold mb-4">{result.phone_number}</p>
            <p className="text-xs text-gray-400 mb-6">Callers dial this number. It's already wired up.</p>
          </>
        ) : (
          <>
            <p className="text-sm text-gray-500 mb-1">Twilio webhook URL</p>
            <code className="block bg-gray-100 rounded p-3 text-sm break-all mb-2">
              {result.webhook_url ?? 'Deploying… check dashboard in ~30s'}
            </code>
            <p className="text-xs text-gray-400 mb-6">
              No Twilio credentials provided — point your own number's Voice webhook here.
            </p>
          </>
        )}

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
        Provide your credentials and we'll deploy a dedicated container, buy a phone number, and wire everything up.
      </p>

      <div className="space-y-4">
        <Field label="Label (optional)" type="text" value={form.label} onChange={set('label')} placeholder="Acme Corp" />

        <Section title="OpenAI">
          <Field label="API key" type="password" value={form.openai_key} onChange={set('openai_key')} placeholder="sk-proj-..." required />
        </Section>

        <Section title="ServiceNow">
          <Field label="Instance name" type="text" value={form.sn_instance} onChange={set('sn_instance')} placeholder="myinstance" required />
          <Field label="Username" type="text" value={form.sn_user} onChange={set('sn_user')} placeholder="admin" required />
          <Field label="Password" type="password" value={form.sn_pass} onChange={set('sn_pass')} placeholder="••••••" required />
        </Section>

        <Section title="Twilio" subtitle="Optional — we'll buy and configure a phone number for you">
          <Field label="Account SID" type="text" value={form.twilio_sid} onChange={set('twilio_sid')} placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" />
          <Field label="Auth token" type="password" value={form.twilio_token} onChange={set('twilio_token')} placeholder="••••••" />
          <div className="mb-3">
            <label className="block text-sm font-medium text-gray-700 mb-1">Country</label>
            <select
              value={form.phone_country}
              onChange={set('phone_country')}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
            >
              {COUNTRIES.map(c => (
                <option key={c.code} value={c.code}>{c.label}</option>
              ))}
            </select>
          </div>
        </Section>

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

function Section({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="border-t pt-4">
      <div className="mb-3">
        <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">{title}</p>
        {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}

function Field({
  label, type, value, onChange, placeholder, required,
}: {
  label: string; type: string; value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  placeholder?: string; required?: boolean
}) {
  return (
    <div className="mb-3">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      <input
        type={type} value={value} onChange={onChange} placeholder={placeholder}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
      />
    </div>
  )
}
