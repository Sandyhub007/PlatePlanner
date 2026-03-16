import "./global.css";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { GluestackUIProvider } from "@gluestack-ui/themed";
import { config } from "@gluestack-ui/config";
import { AuthProvider } from "../src/state/auth";
import { AuthGate } from "../src/state/AuthGate";
import { GestureHandlerRootView } from "react-native-gesture-handler";

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <GluestackUIProvider config={config}>
        <AuthProvider>
          <SafeAreaProvider>
            <AuthGate />
            <Stack screenOptions={{ headerShown: false }}>
              <Stack.Screen name="(tabs)" />
              <Stack.Screen name="(auth)" />
              <Stack.Screen
                name="recipe-detail"
                options={{
                  presentation: "modal",
                  animation: "slide_from_bottom",
                }}
              />
              <Stack.Screen
                name="insights"
                options={{ animation: "slide_from_right" }}
              />
              <Stack.Screen
                name="meal-log"
                options={{ animation: "slide_from_right" }}
              />
              <Stack.Screen
                name="nutrition-goals"
                options={{ animation: "slide_from_right" }}
              />
              <Stack.Screen
                name="progress"
                options={{ animation: "slide_from_right" }}
              />
            </Stack>
            <StatusBar style="auto" />
          </SafeAreaProvider>
        </AuthProvider>
      </GluestackUIProvider>
    </GestureHandlerRootView>
  );
}

