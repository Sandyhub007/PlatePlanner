import { Platform } from "react-native";
import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as WebBrowser from "expo-web-browser";
import * as Linking from "expo-linking";
import { apiFormRequest, apiRequest } from "../api/client";
import type { TokenResponse, User } from "../api/types";

// Complete auth session for native popup flow
WebBrowser.maybeCompleteAuthSession();

// ——— Google OAuth Config ———
const GOOGLE_WEB_CLIENT_ID =
  "110495970455-uoc1td1d7gdih9k38hho0vilkb6a4emt.apps.googleusercontent.com";
// We use localhost for simulator compatibility.
// This URL must be authorized in Google Cloud Console > Web Client > Authorized redirect URIs
const GOOGLE_REDIRECT_URI_NATIVE = "http://localhost:8081/google-callback.html";
const GOOGLE_REDIRECT_URI_WEB = "http://localhost:8081/google-callback.html";

type AuthContextValue = {
  token: string | null;
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  loginWithGoogle: () => void;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const TOKEN_KEY = "plateplanner.token";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // ——— Sync Google token with our backend ———
  const handleGoogleBackendSync = async (idToken?: string, accessToken?: string) => {
    try {
      setLoading(true);
      const tokenResponse = await apiRequest<TokenResponse>("/auth/google", {
        method: "POST",
        body: { id_token: idToken, access_token: accessToken },
      });

      await AsyncStorage.setItem(TOKEN_KEY, tokenResponse.access_token);
      setToken(tokenResponse.access_token);

      const me = await apiRequest<User>("/users/me", {
        token: tokenResponse.access_token,
      });
      setUser(me);
    } catch (error: any) {
      console.error("[Auth] Backend Google Sync Error:", error);
      const msg = error?.message || "Unknown error";
      if (Platform.OS === "web") {
        alert("Google sign-in failed: " + msg);
      } else {
        const { Alert } = require("react-native");
        Alert.alert("Sign-in Failed", msg);
      }
    } finally {
      setLoading(false);
    }
  };

  // ——— On mount: check sessionStorage (web) or load persisted token ———
  useEffect(() => {
    const load = async () => {
      // Web: check if the static callback page stored Google tokens
      if (Platform.OS === "web" && typeof sessionStorage !== "undefined") {
        const googleAccessToken = sessionStorage.getItem("google_oauth_access_token");
        const googleIdToken = sessionStorage.getItem("google_oauth_id_token");

        if (googleAccessToken || googleIdToken) {
          sessionStorage.removeItem("google_oauth_access_token");
          sessionStorage.removeItem("google_oauth_id_token");
          await handleGoogleBackendSync(
            googleIdToken || undefined,
            googleAccessToken || undefined
          );
          return;
        }
      }

      // Normal flow: check for a stored app token
      const stored = await AsyncStorage.getItem(TOKEN_KEY);
      if (stored) {
        setToken(stored);
        try {
          const me = await apiRequest<User>("/users/me", { token: stored });
          setUser(me);
        } catch {
          await AsyncStorage.removeItem(TOKEN_KEY);
          setToken(null);
        }
      }
      setLoading(false);
    };
    load();
  }, []);

  // ——— Email/password login ———
  const login = async (email: string, password: string) => {
    const tokenResponse = await apiFormRequest<TokenResponse>("/auth/login", {
      username: email,
      password,
    });
    await AsyncStorage.setItem(TOKEN_KEY, tokenResponse.access_token);
    setToken(tokenResponse.access_token);
    const me = await apiRequest<User>("/users/me", {
      token: tokenResponse.access_token,
    });
    setUser(me);
  };

  // ——— Registration ———
  const register = async (email: string, password: string, fullName: string) => {
    await apiRequest<User>("/auth/register", {
      method: "POST",
      body: { email, password, full_name: fullName },
    });
    await login(email, password);
  };

  // ——— Google Sign-In ———
  const loginWithGoogle = async () => {
    if (Platform.OS === "web") {
      // Web: direct redirect to Google → static callback page
      const authUrl =
        `https://accounts.google.com/o/oauth2/v2/auth?` +
        `client_id=${encodeURIComponent(GOOGLE_WEB_CLIENT_ID)}` +
        `&redirect_uri=${encodeURIComponent(GOOGLE_REDIRECT_URI_WEB)}` +
        `&response_type=token` +
        `&scope=${encodeURIComponent("openid profile email")}`;
      window.location.href = authUrl;
    } else {
      // Native (iOS/Android): use WebBrowser with intermediate redirect + deep link return
      try {
        // Generate a deep link back to the app (e.g. exp://.../--/)
        const returnUrl = Linking.createURL("/");
        console.log("[Auth] Return URL:", returnUrl);

        // Pass this return URL as 'state' to Google
        // Google -> google-callback.html -> detects state -> redirects to returnUrl
        const authUrl =
          `https://accounts.google.com/o/oauth2/v2/auth?` +
          `client_id=${encodeURIComponent(GOOGLE_WEB_CLIENT_ID)}` +
          `&redirect_uri=${encodeURIComponent(GOOGLE_REDIRECT_URI_NATIVE)}` +
          `&response_type=token` +
          `&scope=${encodeURIComponent("openid profile email")}` +
          `&state=${encodeURIComponent(returnUrl)}`;

        const result = await WebBrowser.openAuthSessionAsync(authUrl, returnUrl);

        if (result.type === "success" && result.url) {
          // Parse tokens from the deep link URL query params
          // result.url will look like: exp://...?access_token=...&id_token=...
          const { queryParams } = Linking.parse(result.url);
          const accessToken = queryParams?.access_token;
          const idToken = queryParams?.id_token;

          if (accessToken || idToken) {
            // Need to cast to string as Linking.parse can return string[]
            const at = Array.isArray(accessToken) ? accessToken[0] : accessToken;
            const it = Array.isArray(idToken) ? idToken[0] : idToken;

            await handleGoogleBackendSync(it || undefined, at || undefined);
          }
        }
      } catch (error) {
        console.error("[Auth] Google Sign-In error:", error);
      }
    }
  };

  // ——— Logout ———
  const logout = async () => {
    await AsyncStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  };

  const value = useMemo(
    () => ({ token, user, loading, login, register, loginWithGoogle, logout }),
    [token, user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
