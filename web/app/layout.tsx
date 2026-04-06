import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Call Center Jared Platform',
  description: 'Multi-tenant AI voice assistant provisioning',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        <header className="border-b bg-white px-6 py-4">
          <span className="font-semibold tracking-tight">Call Center Jared Platform</span>
        </header>
        <main className="mx-auto max-w-4xl px-6 py-10">{children}</main>
      </body>
    </html>
  )
}
