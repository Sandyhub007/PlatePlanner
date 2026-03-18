import { ExpoConfig, ConfigContext } from "expo/config";

// app.config.ts layers dynamic values on top of the static app.json.
// Expo loads app.json first, then applies this function's return value.
// See: https://docs.expo.dev/workflow/configuration/#dynamic-configuration

export default ({ config }: ConfigContext): ExpoConfig => ({
  // Spread the entire static app.json config as the base
  ...config,

  // Required fields (already in app.json, listed here for TS satisfaction)
  name: config.name ?? "PlatePlanner",
  slug: config.slug ?? "plate-planner-mobile",

  // Merge extra with the dynamic API URL from env vars
  extra: {
    ...config.extra,
    // Makes the API URL available via Constants.expoConfig.extra.apiUrl
    apiUrl: process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000",
  },
});
