/** Decode JWT `sub` without verifying the signature (server validates on API calls). */
export function jwtSub(jwt: string | null): string | null {
  if (!jwt) return null;
  const parts = jwt.split('.');
  if (parts.length < 2) return null;
  try {
    let b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const pad = (4 - (b64.length % 4)) % 4;
    if (pad) b64 += '='.repeat(pad);
    const json = JSON.parse(atob(b64)) as { sub?: unknown };
    const sub = json.sub;
    if (typeof sub === 'string') return sub;
    if (sub != null && (typeof sub === 'number' || typeof sub === 'boolean')) return String(sub);
    return null;
  } catch {
    return null;
  }
}
