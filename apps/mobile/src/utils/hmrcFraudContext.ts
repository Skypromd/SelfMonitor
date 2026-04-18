import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import * as Localization from 'expo-localization';
import { Platform } from 'react-native';

const DEVICE_ID_KEY = 'hmrc_fraud_device_id_v1';

function randomUuid(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export async function buildMobileHmrcFraudClientContext(): Promise<Record<string, unknown>> {
  let deviceId = await AsyncStorage.getItem(DEVICE_ID_KEY);
  if (!deviceId) {
    deviceId = randomUuid();
    await AsyncStorage.setItem(DEVICE_ID_KEY, deviceId);
  }
  const ver = Constants.expoConfig?.version ?? '1.0.0';
  const locale = Localization.getLocales()[0]?.languageTag;
  const tz =
    typeof Intl !== 'undefined' ? Intl.DateTimeFormat().resolvedOptions().timeZone : undefined;
  return {
    client_type: 'mobile',
    user_agent: `MyNetTaxMobile/${ver} (${Platform.OS} ${Platform.Version})`,
    app_version: ver,
    device_id: deviceId,
    os_name_version: `${Platform.OS} ${String(Platform.Version)}`,
    timezone: tz,
    locale,
    request_timestamp_utc: new Date().toISOString(),
  };
}
