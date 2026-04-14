import { useRouter } from 'next/router';
import { useEffect } from 'react';
import AdminConsole, { type AdminPageProps } from '../../components/AdminConsole';
import { LEGACY_QUERY_TAB_TO_PATH } from '../../lib/adminRoutes';

type Props = Omit<AdminPageProps, 'section'>;

export default function AdminOverviewPage(props: Props) {
  const router = useRouter();

  useEffect(() => {
    if (!router.isReady) return;
    const raw = router.query.tab;
    const q = typeof raw === 'string' ? raw : Array.isArray(raw) ? raw[0] : '';
    if (!q || !LEGACY_QUERY_TAB_TO_PATH[q]) return;
    const dest = LEGACY_QUERY_TAB_TO_PATH[q];
    void router.replace(dest);
  }, [router.isReady, router.query.tab, router]);

  return <AdminConsole {...props} section="overview" />;
}
