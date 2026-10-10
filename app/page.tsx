import {redirect} from 'next/navigation';
import {defaultLocale} from '@/i18n/request';

export default function RootPage() {
  redirect(`/${defaultLocale}`);
}
