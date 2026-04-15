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

    const id = setInterval(() => {
      Network.getNetworkStateAsync().then(updateStatus).catch(() => {
        return;
      });
    }, 8000);

    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  const isOffline = !status.isConnected || status.isInternetReachable === false;

  return { ...status, isOffline };
}
