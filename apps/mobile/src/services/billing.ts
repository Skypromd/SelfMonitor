import { Linking } from 'react-native';

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
