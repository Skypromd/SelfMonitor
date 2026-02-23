import { useEffect, useState } from 'react';
import * as Network from 'expo-network';

type NetworkStatus = {
  isConnected: boolean;
  isInternetReachable: boolean;
};

const DEFAULT_STATUS: NetworkStatus = {
  isConnected: true,
  isInternetReachable: true,
};

export function useNetworkStatus() {
  const [status, setStatus] = useState<NetworkStatus>(DEFAULT_STATUS);

  useEffect(() => {
    let mounted = true;

    const updateStatus = (state: Network.NetworkState) => {
      if (!mounted) return;
      setStatus({
        isConnected: state.isConnected ?? false,
        isInternetReachable: state.isInternetReachable ?? true,
      });
    };

    Network.getNetworkStateAsync().then(updateStatus).catch(() => {
      return;
    });

    const subscription = Network.addNetworkStateListener
      ? Network.addNetworkStateListener(updateStatus)
      : null;

    return () => {
      mounted = false;
      if (subscription && 'remove' in subscription) {
        subscription.remove();
      }
    };
  }, []);

  const isOffline = !status.isConnected || status.isInternetReachable === false;

  return { ...status, isOffline };
}
