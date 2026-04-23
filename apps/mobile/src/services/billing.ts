import { Linking } from 'react-native';

import { API_GATEWAY_URL } from './api';

const MONTHLY_CHECKOUT_URL = process.env.EXPO_PUBLIC_STRIPE_CHECKOUT_URL;
const ANNUAL_CHECKOUT_URL = process.env.EXPO_PUBLIC_STRIPE_CHECKOUT_ANNUAL_URL || MONTHLY_CHECKOUT_URL;
const BILLING_PORTAL_URL = process.env.EXPO_PUBLIC_STRIPE_PORTAL_URL;

export type BillingCycle = 'monthly' | 'annual';

export const hasBillingCheckout = () => Boolean(MONTHLY_CHECKOUT_URL || ANNUAL_CHECKOUT_URL);

export const openCheckout = async (cycle: BillingCycle) => {
  const url = cycle === 'annual' ? ANNUAL_CHECKOUT_URL : MONTHLY_CHECKOUT_URL;
  if (!url) return false;
  try {
    await Linking.openURL(url);
    return true;
  } catch {
    return false;
  }
};

export const openBillingPortal = async () => {
  if (!BILLING_PORTAL_URL) return false;
  try {
    await Linking.openURL(BILLING_PORTAL_URL);
    return true;
  } catch {
    return false;
  }
};

export type BillingAddonConsult = {
  name: string;
  amount_pence: number;
  sla_note?: string;
};

export async function fetchBillingAddons(): Promise<{ accountant_cis_consult?: BillingAddonConsult } | null> {
  try {
    const res = await fetch(`${API_GATEWAY_URL}/billing/addons`);
    if (!res.ok) return null;
    return (await res.json()) as { accountant_cis_consult?: BillingAddonConsult };
  } catch {
    return null;
  }
}

export type BillingSubscriptionPayload = {
  plan?: string;
  status?: string;
  current_period_end?: number | null;
  account_credit_balance_gbp?: number;
  accountant_consult_sessions_available?: number;
};

export async function fetchBillingSubscription(
  email: string,
  token: string,
): Promise<{ ok: boolean; data?: BillingSubscriptionPayload }> {
  try {
    const res = await fetch(
      `${API_GATEWAY_URL}/billing/subscription/${encodeURIComponent(email)}`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    if (!res.ok) return { ok: false };
    const data = (await res.json()) as BillingSubscriptionPayload;
    return { ok: true, data };
  } catch {
    return { ok: false };
  }
}

export async function createAccountantConsultCheckout(email: string): Promise<{
  ok: boolean;
  checkout_url?: string;
  detail?: string;
}> {
  try {
    const res = await fetch(`${API_GATEWAY_URL}/billing/checkout/session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product: 'accountant_cis_consult', email }),
    });
    const payload = (await res.json().catch(() => ({}))) as {
      checkout_url?: string;
      detail?: string | { msg?: string };
    };
    if (!res.ok) {
      const d = payload.detail;
      const msg = typeof d === 'string' ? d : 'Checkout failed';
      return { ok: false, detail: msg };
    }
    if (payload.checkout_url) return { ok: true, checkout_url: payload.checkout_url };
    return { ok: false, detail: 'No checkout URL' };
  } catch {
    return { ok: false, detail: 'Network error' };
  }
}

export const openUrl = async (url: string) => {
  try {
    await Linking.openURL(url);
    return true;
  } catch {
    return false;
  }
};
