export type AdminTab =
  | 'overview'
  | 'subscriptions'
  | 'users'
  | 'billing'
  | 'leadops'
  | 'invoices'
  | 'ai-agent'
  | 'health'
  | 'support'
  | 'regulatory';

export const ADMIN_SECTION_PATH: Record<AdminTab, string> = {
  overview: '/admin',
  subscriptions: '/admin/subscriptions',
  users: '/admin/users',
  billing: '/admin/partner-billing',
  leadops: '/admin/lead-ops',
  invoices: '/admin/invoices',
  'ai-agent': '/admin/ai-agent',
  health: '/admin/health',
  support: '/admin/support',
  regulatory: '/admin/regulatory',
};

const PATH_TO_TAB: Record<string, AdminTab> = {
  '/admin': 'overview',
  '/admin/subscriptions': 'subscriptions',
  '/admin/users': 'users',
  '/admin/partner-billing': 'billing',
  '/admin/lead-ops': 'leadops',
  '/admin/invoices': 'invoices',
  '/admin/ai-agent': 'ai-agent',
  '/admin/health': 'health',
  '/admin/support': 'support',
  '/admin/regulatory': 'regulatory',
};

export function adminTabFromPathname(pathname: string): AdminTab | null {
  const key = pathname.replace(/\/$/, '') || '/admin';
  return PATH_TO_TAB[key] ?? null;
}

export const LEGACY_QUERY_TAB_TO_PATH: Partial<Record<string, string>> = {
  overview: '/admin',
  subscriptions: '/admin/subscriptions',
  users: '/admin/users',
  billing: '/admin/partner-billing',
  leadops: '/admin/lead-ops',
  invoices: '/admin/invoices',
  'ai-agent': '/admin/ai-agent',
  health: '/admin/health',
  support: '/admin/support',
  regulatory: '/admin/regulatory',
};
