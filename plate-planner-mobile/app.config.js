// Dynamic Expo configuration for PlatePlanner
// This file extends app.json and injects environment-specific values at build time.
// Environment variables are set in eas.json per build profile, or can be overridden locally.

const IS_DEV = process.env.APP_ENV === "development";
const IS_PREVIEW = process.env.APP_ENV === "preview";
const IS_PRODUCTION = process.env.APP_ENV === "production";

const getApiUrl = () => {
  if (process.env.API_URL) {
    return process.env.API_URL;
  }
  if (IS_PRODUCTION) {
    return "https://api.plateplanner.app";
  }
  if (IS_PREVIEW) {
    return "https://api-staging.plateplanner.app";
  }
  // Default to localhost for development
  return "http://localhost:8000";
};

const getAppName = () => {
  if (IS_DEV) return "PlatePlanner (Dev)";
  if (IS_PREVIEW) return "PlatePlanner (Preview)";
  return "PlatePlanner";
};

const getBundleIdentifier = () => {
  if (IS_DEV) return "com.plateplanner.app.dev";
  if (IS_PREVIEW) return "com.plateplanner.app.preview";
  return "com.plateplanner.app";
};

export default ({ config }) => {
  return {
    ...config,
    name: getAppName(),
    extra: {
      ...config.extra,
      apiUrl: getApiUrl(),
      appEnv: process.env.APP_ENV || "development",
    },
    ios: {
      ...config.ios,
      bundleIdentifier: getBundleIdentifier(),
    },
    android: {
      ...config.android,
      package: getBundleIdentifier(),
    },
  };
};
