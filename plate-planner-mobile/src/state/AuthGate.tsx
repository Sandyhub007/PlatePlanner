import { useEffect } from "react";
import { useRouter, useSegments } from "expo-router";
import { useAuth } from "./auth";

export function AuthGate() {
  const { token, loading } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    const inAuthGroup = segments[0] === "(auth)";
    if (!token && !inAuthGroup) {
      router.replace("/(auth)/login");
    }
    if (token && inAuthGroup) {
      router.replace("/(tabs)");
    }
  }, [token, loading, segments, router]);

  return null;
}
