# Google Sign-In Setup Guide

To enable Google Sign-In in PlatePlanner, you need to configure a project in Google Cloud Console and update the client IDs in the code.

## 1. Create a Google Cloud Project
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g., `plateplanner-mobile`).
3. Navigation to **APIs & Services** > **OAuth consent screen**.
   - Select **External** (unless you have a Google Workspace org).
   - Fill in the App Name (`PlatePlanner`), Support Email, and Developer Contact Info.
   - Click **Save and Continue**.
4. Skip "Scopes" unless you need specific drive/calendar access (default `profile` and `email` are fine).
5. Add your email to "Test Users" if the app is in "Testing" mode.

## 2. Create OAuth Credentials
Go to **APIs & Services** > **Credentials** > **Create Credentials** > **OAuth client ID**.

### For iOS
1. Select **iOS**.
2. Bundle ID: `com.anonymous.plate-planner-mobile` (check `app.json` or run `npx expo config --type public` to see the bundle identifier).
   - *Note: If using Expo Go, you don't need a specific Bundle ID, but for standalone builds you do.*
3. Copy the **Client ID** (ends in `...apps.googleusercontent.com`).

### For Android
1. Select **Android**.
2. Package Name: match your `app.json` (e.g., `com.anonymous.plate-planner-mobile`).
3. SHA-1 Certificate Fingerprint: 
   - For development: Run `cd android && ./gradlew signingReport` (if you have an android folder) or use Expo's credentials.
   - For Expo Go: You don't strict enforcement, but you might need to use the Web Client ID for Expo Go proxy.
4. Copy the **Client ID**.

### For Web (and Expo Go Proxy)
1. Select **Web application**.
2. Authorized JavaScript origins: `http://localhost:8081` (for dev).
3. Authorized redirect URIs: 
   - `https://auth.expo.io/@your-username/plate-planner-mobile` (if using Expo Auth proxy).
   - `http://localhost:8081`
4. Copy the **Client ID**.

## 3. Update Code
Open `/src/state/auth.tsx` and replace the placeholders:

```typescript
const [request, response, promptAsync] = Google.useAuthRequest({
    androidClientId: "YOUR_ANDROID_CLIENT_ID.apps.googleusercontent.com",
    iosClientId: "YOUR_IOS_CLIENT_ID.apps.googleusercontent.com",
    webClientId: "YOUR_WEB_CLIENT_ID.apps.googleusercontent.com",
});
```

## 4. Backend Configuration
The backend (`/auth/google`) verifies the ID token.
- Ensure your backend server's time is synchronized (NTP).
- The current implementation accepts tokens from **any** client ID. For production security, update `src/api/routers/auth.py` to verify the `aud` (audience) claim matches your Client IDs.

## Troubleshooting
- **Error 400: redirect_uri_mismatch**: Ensure the redirect URI in Google Console matches exactly what Expo relies on.
- **Expo Go**: Google Sign-In on Expo Go often requires using the **Web Client ID** rather than native IDs because it runs inside the Expo container.
