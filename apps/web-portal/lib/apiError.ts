/**
 * Standardised user-facing API error messages.
 *
 * Usage:
 *   import { formatApiError } from '../lib/apiError';
 *   catch (err) { setError(formatApiError(err, 'load reports')); }
 */

export function formatApiError(err: unknown, context?: string): string {
  if (err instanceof TypeError && err.message.toLowerCase().includes('fetch')) {
    return 'Unable to connect — check your internet connection and try again.';
  }
  if (err instanceof Error) {
    const msg = err.message;
    if (msg.includes('401') || msg.toLowerCase().includes('unauthori')) {
      return 'Session expired — please log in again.';
    }
    if (msg.includes('403') || msg.toLowerCase().includes('forbidden')) {
      return "You don't have access to this feature. Check your subscription plan.";
    }
    if (msg.includes('429')) {
      return 'Too many requests — please wait a moment and try again.';
    }
    if (msg.includes('503') || msg.includes('504') || msg.includes('502')) {
      return 'Service temporarily unavailable — please try again in a few minutes.';
    }
    if (msg) return msg;
  }
  return context
    ? `Could not ${context} — please try again.`
    : 'Something went wrong — please try again.';
}
