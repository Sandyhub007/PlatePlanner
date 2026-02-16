import { Tabs } from "expo-router";
import { Home, Utensils, Calendar, ShoppingCart, User, Plus } from "lucide-react-native";
import { View, Platform } from "react-native";

export default function TabLayout() {
  const activeColor = "#16a34a"; // Green-600
  const inactiveColor = "#9CA3AF"; // Gray-400

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: activeColor,
        tabBarInactiveTintColor: inactiveColor,
        tabBarShowLabel: false,
        tabBarStyle: {
          position: 'absolute',
          bottom: 20,
          left: 20,
          right: 20,
          elevation: 0,
          backgroundColor: '#ffffff',
          borderRadius: 25,
          height: 70,
          shadowColor: "#000",
          shadowOffset: {
            width: 0,
            height: 10,
          },
          shadowOpacity: 0.1,
          shadowRadius: 10,
          borderTopWidth: 0,
          paddingBottom: 0, // Reset default padding
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          tabBarIcon: ({ color, focused }) => (
            <View className={`items-center justify-center ${focused ? 'bg-green-50 p-2 rounded-xl' : ''}`}>
              <Home size={24} color={color} strokeWidth={focused ? 2.5 : 2} />
            </View>
          ),
        }}
      />
      <Tabs.Screen
        name="recipes"
        options={{
          tabBarIcon: ({ color, focused }) => (
            <View className={`items-center justify-center ${focused ? 'bg-green-50 p-2 rounded-xl' : ''}`}>
              <Utensils size={24} color={color} strokeWidth={focused ? 2.5 : 2} />
            </View>
          ),
        }}
      />

      {/* The Central FAB */}
      <Tabs.Screen
        name="planner"
        options={{
          tabBarIcon: () => (
            <View
              className="bg-green-500 w-14 h-14 rounded-full items-center justify-center shadow-lg shadow-green-200"
              style={{ marginBottom: 30 }} // Float it up
            >
              <Plus size={30} color="white" strokeWidth={3} />
            </View>
          ),
        }}
      />

      <Tabs.Screen
        name="shopping"
        options={{
          tabBarIcon: ({ color, focused }) => (
            <View className={`items-center justify-center ${focused ? 'bg-gray-100 p-2 rounded-xl' : ''}`}>
              <ShoppingCart size={24} color={color} strokeWidth={focused ? 2.5 : 2} />
            </View>
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          tabBarIcon: ({ color, focused }) => (
            <View className={`items-center justify-center ${focused ? 'bg-gray-100 p-2 rounded-xl' : ''}`}>
              <User size={24} color={color} strokeWidth={focused ? 2.5 : 2} />
            </View>
          ),
        }}
      />
    </Tabs>
  );
}
