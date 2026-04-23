/**
 * Операторский поддомен (по умолчанию practolog.* — неочевидное имя вместо admin.*).
 * Другой origin → другой sessionStorage. Включается NEXT_PUBLIC_ADMIN_SUBDOMAIN_ENABLED=1.
 */

export const ADMIN_SUBDOMAIN_ENABLED =
  typeof process !== 'undefined' && process.env.NEXT_PUBLIC_ADMIN_SUBDOMAIN_ENABLED === '1';

export function adminHostPattern(): string {
  return (process.env.NEXT_PUBLIC_ADMIN_HOST || 'practolog.localhost').toLowerCase();
}

export function clientOrigin(): string {
  return (process.env.NEXT_PUBLIC_CLIENT_ORIGIN || '').replace(/\/$/, '');
}

export function adminOrigin(): string {
  return (process.env.NEXT_PUBLIC_ADMIN_ORIGIN || '').replace(/\/$/, '');
}

export function isAdminHostname(hostname: string): boolean {
  if (!ADMIN_SUBDOMAIN_ENABLED) return false;
  return hostname.toLowerCase() === adminHostPattern();
}

/** Ссылка на экран оператора (/admin, /admin/login, /billing). */
export function adminSurfaceUrl(path: string): string {
  const p = path.startsWith('/') ? path : `/${path}`;
  const base = adminOrigin();
  if (ADMIN_SUBDOMAIN_ENABLED && base) return `${base}${p}`;
  return p;
}

/** Ссылка на клиентское приложение. */
export function clientSurfaceUrl(path: string): string {
  const p = path.startsWith('/') ? path : `/${path}`;
  const base = clientOrigin();
  if (ADMIN_SUBDOMAIN_ENABLED && base) return `${base}${p}`;
  return p;
}

/** После простоя на странице /admin: куда выкинуть сессию. */
export function inactivityLogoutLocation(): string {
  if (typeof window === 'undefined') {
    return adminSurfaceUrl('/admin/login?reason=inactivity');
  }
  if (isAdminHostname(window.location.hostname)) {
    return adminSurfaceUrl('/admin/login?reason=inactivity');
  }
  return '/?reason=inactivity';
}
