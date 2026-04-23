import * as Linking from 'expo-linking';
import * as WebBrowser from 'expo-web-browser';

WebBrowser.maybeCompleteAuthSession();

const CALLBACK_SEGMENT = 'banking-callback';

export function bankingRedirectUri(): string {
  return Linking.createURL(CALLBACK_SEGMENT, { scheme: 'selfmonitor' });
}

export type BankingCallbackParams = {
  code?: string;
  connectionId?: string;
  error?: string;
};

export function parseBankingCallbackUrl(url: string): BankingCallbackParams {
  const parsed = Linking.parse(url);
  const q = parsed.queryParams ?? {};
  const err = q.error;
  const code = q.code;
  const connectionId = q.connection_id;
  return {
    error: typeof err === 'string' ? err : Array.isArray(err) ? err[0] : undefined,
    code: typeof code === 'string' ? code : Array.isArray(code) ? code[0] : undefined,
    connectionId:
      typeof connectionId === 'string'
        ? connectionId
        : Array.isArray(connectionId)
          ? connectionId[0]
          : undefined,
  };
}

export async function openBankingAuthSession(
  consentUrl: string,
  redirectUri: string,
): Promise<WebBrowser.WebBrowserAuthSessionResult> {
  return WebBrowser.openAuthSessionAsync(consentUrl, redirectUri);
}

export function bankingCallbackQueryString(params: BankingCallbackParams): string {
  if (params.error) {
    throw new Error(String(params.error));
  }
  if (params.connectionId) {
    return `connection_id=${encodeURIComponent(params.connectionId)}`;
  }
  if (params.code) {
    return `code=${encodeURIComponent(params.code)}`;
  }
  throw new Error('Bank callback missing code and connection_id');
}
