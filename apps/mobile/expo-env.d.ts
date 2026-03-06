// Expo replaces process.env.EXPO_PUBLIC_* at build time via Babel.
// This declaration tells TypeScript that `process` is available in the Expo bundle.
declare const process: {
  env: Record<string, string | undefined>;
};
