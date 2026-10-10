import {NextIntlClientProvider} from 'next-intl';
import {getMessages} from 'next-intl/server';
import {notFound} from 'next/navigation';
import {locales} from '@/i18n/request';
import {Analytics} from '@vercel/analytics/next';
import '../globals.css';

export function generateStaticParams() {
  return locales.map((locale) => ({locale}));
}

export default async function LocaleLayout({
  children,
  params
}: {
  children: React.ReactNode;
  params: Promise<{locale: string}>;
}) {
  const resolvedParams = await params;
  const locale = resolvedParams?.locale;

  // Ensure that the incoming `locale` is valid
  if (!locale || !locales.includes(locale as any)) {
    notFound();
  }

  // Providing all messages to the client side
  const messages = await getMessages();

  return (
    <html lang={locale}>
      <body className="antialiased">
        <NextIntlClientProvider messages={messages} locale={locale}>
          {children}
        </NextIntlClientProvider>
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  );
}
