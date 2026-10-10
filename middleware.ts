import createMiddleware from 'next-intl/middleware';
import {locales, defaultLocale} from './i18n/request';

export default createMiddleware({
  // A list of all locales that are supported
  locales,

  // Used when no locale matches
  defaultLocale,

  // Always use locale prefix (e.g., /en, /hi, /mwr)
  localePrefix: 'always'
});

export const config = {
  // Match all pathnames except for
  // - … if they start with `/api`, `/_next` or `/_vercel`
  // - … the ones containing a dot (e.g. `favicon.ico`)
  matcher: ['/((?!api|_next|_vercel|.*\\..*).*)']
};
