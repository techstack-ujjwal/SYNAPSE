import {getRequestConfig} from 'next-intl/server';
import {notFound} from 'next/navigation';

export const locales = [
  'en', 'hi', 'bn', 'te', 'mr', 'ta', 'gu', 'kn', 'ml', 'pa',
  'as', 'or', 'ur', 'sa', 'ne', 'kok', 'mai', 'sd', 'doi', 'ks',
  'ch', 'sat', 'mwr'
] as const;

export type Locale = (typeof locales)[number];

export const defaultLocale: Locale = 'en';

export const localeNames: Record<Locale, string> = {
  en: 'English',
  hi: 'हिन्दी',
  bn: 'বাংলা',
  te: 'తెలుగు',
  mr: 'मराठी',
  ta: 'தமிழ்',
  gu: 'ગુજરાતી',
  kn: 'ಕನ್ನಡ',
  ml: 'മലയാളം',
  pa: 'ਪੰਜਾਬੀ',
  as: 'অসমীয়া',
  or: 'ଓଡ଼ିଆ',
  ur: 'اردو',
  sa: 'संस्कृतम्',
  ne: 'नेपाली',
  kok: 'कोंकणी',
  mai: 'मैथिली',
  sd: 'सिन्धी',
  doi: 'डोगरी',
  ks: 'کٲشُر',
  ch: 'छत्तीसगढ़ी',
  sat: 'संथाली',
  mwr: 'मारवाड़ी'
};

export const languageToLocale: Record<string, Locale> = Object.fromEntries(
  Object.entries(localeNames).map(([code, name]) => [name, code])
) as Record<string, Locale>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value);
}

function deepMerge(base: Record<string, unknown>, override: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = { ...base };
  for (const [key, value] of Object.entries(override)) {
    if (isRecord(value) && isRecord(out[key])) {
      out[key] = deepMerge(out[key] as Record<string, unknown>, value);
    } else {
      out[key] = value;
    }
  }
  return out;
}

export default getRequestConfig(async (params) => {
  let targetLocale = (params as { locale?: string }).locale;
  if (!targetLocale && (params as { requestLocale?: Promise<string> }).requestLocale) {
    targetLocale = await (params as { requestLocale: Promise<string> }).requestLocale;
  }
  if (!targetLocale) {
    targetLocale = defaultLocale;
  }

  if (!locales.includes(targetLocale as Locale)) {
    notFound();
  }

  const validLocale = targetLocale as Locale;
  const baseMessages = (await import('../messages/en.json')).default as Record<string, unknown>;
  let localeMessages: Record<string, unknown> = {};
  try {
    localeMessages = (await import(`../messages/${validLocale}.json`)).default as Record<string, unknown>;
  } catch {
    localeMessages = {};
  }

  return {
    locale: validLocale,
    messages: deepMerge(baseMessages, localeMessages)
  };
});
