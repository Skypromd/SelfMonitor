import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

const LOCALES = new Set([
  'ru-RU',
  'en-GB',
  'pl-PL',
  'ro-RO',
  'it-IT',
  'pt-PT',
  'es-ES',
  'tr-TR',
  'bn-BD',
  'uk-UA',
]);

function stripLocalePrefix(pathname: string): string {
  const parts = pathname.split('/').filter(Boolean);
  if (parts.length >= 1 && LOCALES.has(parts[0])) {
    if (parts.length === 1) return '/';
    return `/${parts.slice(1).join('/')}`;
  }
  return pathname;
}

function hostnameOf(req: NextRequest): string {
  const h = req.headers.get('host') || '';
  return h.split(':')[0].toLowerCase();
}

function isStaticPath(pathname: string): boolean {
  return /\.(ico|png|jpg|jpeg|svg|gif|webp|woff2?|ttf|eot|json)$/i.test(pathname);
}

export function middleware(request: NextRequest) {
  const enabled = process.env.NEXT_PUBLIC_ADMIN_SUBDOMAIN_ENABLED === '1';
  if (!enabled) {
    return NextResponse.next();
  }

  const adminHost = (process.env.NEXT_PUBLIC_ADMIN_HOST || 'practolog.localhost').toLowerCase();
  const clientOrigin = (process.env.NEXT_PUBLIC_CLIENT_ORIGIN || 'http://localhost:3000').replace(/\/$/, '');
  const adminOrigin = (process.env.NEXT_PUBLIC_ADMIN_ORIGIN || 'http://practolog.localhost:3000').replace(/\/$/, '');

  const rawPath = request.nextUrl.pathname;
  const search = request.nextUrl.search;

  if (rawPath.startsWith('/_next') || rawPath.startsWith('/api') || rawPath === '/favicon.ico' || isStaticPath(rawPath)) {
    return NextResponse.next();
  }

  const pathname = stripLocalePrefix(rawPath);
  const host = hostnameOf(request);
  const isAdminHost = host === adminHost;

  const isAdminSurfacePath =
    pathname.startsWith('/admin') || pathname === '/billing' || pathname.startsWith('/billing/');

  const clientOnlyPublic = new Set([
    '/',
    '/register',
    '/login',
    '/welcome',
    '/checkout-success',
    '/checkout-cancel',
    '/forgot-password',
    '/reset-password',
  ]);

  if (isAdminHost) {
    if (clientOnlyPublic.has(pathname)) {
      return NextResponse.redirect(new URL(`${rawPath}${search}`, clientOrigin));
    }
    const allowedOnAdminHost = isAdminSurfacePath || isStaticPath(rawPath);
    if (!allowedOnAdminHost) {
      return NextResponse.redirect(new URL(`${rawPath}${search}`, clientOrigin));
    }
    return NextResponse.next();
  }

  if (isAdminSurfacePath) {
    return NextResponse.redirect(new URL(`${rawPath}${search}`, adminOrigin));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
