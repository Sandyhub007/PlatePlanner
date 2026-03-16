import { Platform } from "react-native";
import Constants from "expo-constants";

// ── Production API URL ─────────────────────────────────────────────────────────
// Set this to your deployed backend URL for production builds.
// Override at build time by setting `extra.apiUrl` in app.json or via EAS env.
const PROD_API_URL = "https://api.plateplanner.com";

// ── Dev configuration ──────────────────────────────────────────────────────────
// Your computer's local IP — needed for physical devices on the same WiFi.
const LOCAL_IP = "10.251.101.130";

// iOS Simulator can use localhost; physical devices need the actual IP.
const isSimulator = !Constants.isDevice;

const DEV_API_URL = Platform.select({
  ios: isSimulator ? "http://localhost:8000" : `http://${LOCAL_IP}:8000`,
  android: isSimulator ? "http://10.0.2.2:8000" : `http://${LOCAL_IP}:8000`,
  default: "http://localhost:8000", // Web
})!;

// ── Resolve the API URL ────────────────────────────────────────────────────────
// Priority order:
// 1. app.json > extra.apiUrl — if set to a non-localhost value, use it
// 2. __DEV__ mode -> local dev URL
// 3. Production build -> PROD_API_URL
function resolveApiUrl(): string {
  const configuredUrl = Constants.expoConfig?.extra?.apiUrl as
    | string
    | undefined;

  // If a production URL was explicitly configured in app.json, use it
  if (configuredUrl && !configuredUrl.includes("localhost")) {
    return configuredUrl;
  }

  // In development mode, use the dev URL
  if (__DEV__) {
    return DEV_API_URL;
  }

  // Production builds use the production URL
  return PROD_API_URL;
}

export const API_BASE_URL = resolveApiUrl();
