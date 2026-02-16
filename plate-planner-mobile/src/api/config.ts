import { Platform } from "react-native";
import Constants from "expo-constants";

// Your computer's local IP — needed for physical devices on the same WiFi
const LOCAL_IP = "10.0.0.162";

// iOS Simulator can use localhost; physical devices need the actual IP
const isSimulator = !Constants.isDevice;

const DEV_API_URL = Platform.select({
  ios: isSimulator ? "http://localhost:8000" : `http://${LOCAL_IP}:8000`,
  android: isSimulator ? "http://10.0.2.2:8000" : `http://${LOCAL_IP}:8000`,
  default: "http://localhost:8000", // Web
});

export const API_BASE_URL = DEV_API_URL!;
