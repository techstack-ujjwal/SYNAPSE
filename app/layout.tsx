import type { Metadata, Viewport } from 'next'

export const metadata: Metadata = {
  title: 'Synapse AI · Care starts with a conversation',
  description: 'Multilingual hospital intake with voice, report analysis, and clinician handoff.',
  icons: {
    icon: [
      { url: '/icon-light-32x32.png', media: '(prefers-color-scheme: light)' },
      { url: '/icon-dark-32x32.png', media: '(prefers-color-scheme: dark)' },
      { url: '/icon.svg', type: 'image/svg+xml' },
    ],
    apple: '/apple-icon.png',
  },
}

export const viewport: Viewport = {
  colorScheme: 'light',
  themeColor: '#f5f1e8',
  width: 'device-width',
  initialScale: 1,
  userScalable: false,
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return children
}
