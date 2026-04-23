/** Shared auth token exchange (user + admin login pages). */

export const AUTH_SERVICE_URL =
  process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || '/api/auth';

export type LoginTokenResult =
  | { ok: true; access_token: string; status: number }
  | { ok: false; status: number; detail?: string };

export async function loginWithPassword(params: {
  email: string;
  password: string;
  totpCode?: string;
}): Promise<LoginTokenResult> {
  const formData = new URLSearchParams();
  formData.append('username', params.email.trim());
  formData.append('password', params.password);
  if (params.totpCode) {
    formData.append('scope', `totp:${params.totpCode}`);
  }
  const res = await fetch(`${AUTH_SERVICE_URL}/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData.toString(),
  });
  const data = (await res.json().catch(() => ({}))) as {
    access_token?: string;
    detail?: string;
  };
  if (res.ok && data.access_token) {
    return { ok: true, access_token: data.access_token, status: res.status };
  }
  return { ok: false, status: res.status, detail: data.detail };
}
