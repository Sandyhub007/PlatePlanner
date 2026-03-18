import { Platform } from "react-native";
import Constants from "expo-constants";

// ── API URL Resolution ───────────────────────────────────────────────────────
// Priority order:
// 1. EXPO_PUBLIC_API_URL env var (set in .env / .env.production)
// 2. app.config.ts > extra.apiUrl (legacy / EAS override)
// 3. Platform-aware dev fallback (localhost / 10.0.2.2 for Android emulator)

// Dev-only: your machine's LAN IP for physical-device testing over WiFi.
// Only used as a last-resort fallback when no env var is set.
const LOCAL_IP = "10.251.101.130";

const isSimulator = !Constants.isDevice;

/** Platform-aware fallback for local development (no env var set). */
const DEV_FALLBACK_URL = Platform.select({
  ios: isSimulator ? "http://localhost:8000" : `http://${LOCAL_IP}:8000`,
  android: isSimulator ? "http://10.0.2.2:8000" : `http://${LOCAL_IP}:8000`,
  default: "http://localhost:8000", // Web
})!;

function resolveApiUrl(): string {
  // 1. Expo env var (preferred — set via .env / .env.production)
  const envUrl = process.env.EXPO_PUBLIC_API_URL;
  if (envUrl) {
    return envUrl;
  }

  // 2. Legacy: app.config extra.apiUrl (e.g. set via EAS build)
  const configuredUrl = Constants.expoConfig?.extra?.apiUrl as
    | string
    | undefined;
  if (configuredUrl) {
    return configuredUrl;
  }

  // 3. Fallback: platform-aware dev URL
  if (__DEV__) {
    return DEV_FALLBACK_URL;
  }

  // Should not happen if .env.production is set; hard fallback for safety.
  return "https://plateplanner-api.up.railway.app";
}

export const API_BASE_URL = resolveApiUrl();

// ── Google OAuth Redirect URI ────────────────────────────────────────────────
// Also configurable via env var so it can differ between dev and prod.
export const GOOGLE_REDIRECT_URI =
  process.env.EXPO_PUBLIC_GOOGLE_REDIRECT_URI ||
  "http://localhost:8081/google-callback.html";
