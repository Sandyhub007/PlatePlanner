import { ScrollView, Switch, ActivityIndicator, TouchableOpacity } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Box, Text, VStack, HStack, Avatar, AvatarFallbackText, Icon, SettingsIcon, ChevronRightIcon, Button, ButtonText, Divider } from "@gluestack-ui/themed";
import { LogOut } from "lucide-react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useAuth } from "../../src/state/auth";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "expo-router";
import { apiRequest } from "../../src/api/client";

// Maps frontend toggle keys → API restriction strings
const KEY_TO_API: Record<string, string> = {
  vegan: "vegan",
  vegetarian: "vegetarian",
  glutenFree: "gluten_free",
  dairyFree: "dairy_free",
  keto: "keto",
};

type Prefs = {
  vegan: boolean;
  vegetarian: boolean;
  glutenFree: boolean;
  dairyFree: boolean;
  keto: boolean;
};

const CUISINE_OPTIONS = [
  "Indian", "Italian", "Mexican", "Thai", "Japanese",
  "Mediterranean", "American", "Chinese", "Korean",
  "Middle Eastern", "French", "Greek", "Vietnamese",
];

const ALLERGY_OPTIONS = [
  "Peanuts", "Tree Nuts", "Milk", "Eggs", "Wheat",
  "Soy", "Fish", "Shellfish", "Sesame",
];

function restrictionsToPrefs(restrictions: string[]): Prefs {
  const set = new Set(restrictions);
  return {
    vegan: set.has("vegan"),
    vegetarian: set.has("vegetarian"),
    glutenFree: set.has("gluten_free"),
    dairyFree: set.has("dairy_free"),
    keto: set.has("keto"),
  };
}

function prefsToRestrictions(prefs: Prefs): string[] {
  return Object.entries(KEY_TO_API)
    .filter(([key]) => prefs[key as keyof Prefs])
    .map(([, apiVal]) => apiVal);
}

export default function ProfileScreen() {
  const { user, token, logout } = useAuth();
  const router = useRouter();

  const [preferences, setPreferences] = useState<Prefs>({
    vegan: false,
    vegetarian: false,
    glutenFree: false,
    dairyFree: false,
    keto: false,
  });
  const [cuisinePrefs, setCuisinePrefs] = useState<string[]>([]);
  const [allergies, setAllergies] = useState<string[]>([]);
  const [loadingPrefs, setLoadingPrefs] = useState(false);
  const [savingPrefs, setSavingPrefs] = useState(false);

  // Track if we've loaded initial prefs so we don't trigger a save on first render
  const initialLoadDone = useRef(false);

  const initials = user?.full_name
    ? user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : "U";

  // Load preferences on mount
  useEffect(() => {
    if (!token) return;
    setLoadingPrefs(true);
    apiRequest<{
      dietary_restrictions: string[];
      cuisine_preferences: string[];
      allergies: string[];
    }>("/users/me/preferences", { token })
      .then(data => {
        setPreferences(restrictionsToPrefs(data.dietary_restrictions || []));
        setCuisinePrefs(data.cuisine_preferences || []);
        setAllergies(data.allergies || []);
        initialLoadDone.current = true;
      })
      .catch(err => {
        console.log("Failed to load preferences:", err?.message);
        initialLoadDone.current = true;
      })
      .finally(() => setLoadingPrefs(false));
  }, [token]);

  // Save preferences to API whenever they change (after initial load)
  useEffect(() => {
    if (!initialLoadDone.current || !token) return;
    const restrictions = prefsToRestrictions(preferences);
    setSavingPrefs(true);
    apiRequest("/users/me/preferences", {
      method: "PUT",
      token,
      body: {
        dietary_restrictions: restrictions,
        cuisine_preferences: cuisinePrefs,
        allergies: allergies,
      },
    })
      .catch(err => console.log("Failed to save preferences:", err?.message))
      .finally(() => setSavingPrefs(false));
  }, [preferences, cuisinePrefs, allergies]);

  const togglePreference = (key: keyof Prefs) => {
    setPreferences(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const toggleCuisine = (cuisine: string) => {
    setCuisinePrefs(prev =>
      prev.includes(cuisine) ? prev.filter(c => c !== cuisine) : [...prev, cuisine]
    );
  };

  const toggleAllergy = (allergy: string) => {
    setAllergies(prev =>
      prev.includes(allergy) ? prev.filter(a => a !== allergy) : [...prev, allergy]
    );
  };

  const handleLogout = async () => {
    await logout();
    router.replace("/(auth)/login");
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#FAFAFA' }} edges={["top", "left", "right"]}>
      <ScrollView contentContainerStyle={{ paddingBottom: 100 }} showsVerticalScrollIndicator={false}>

        {/* Profile Header */}
        <Box px="$6" pt="$4" pb="$6">
          <HStack alignItems="center" justifyContent="space-between" mb="$6">
            <Text size="3xl" bold color="$coolGray900">Profile</Text>
            <Box p="$2" bg="$coolGray100" borderRadius="$full">
              <Icon as={SettingsIcon} color="$coolGray600" />
            </Box>
          </HStack>

          <HStack space="md" alignItems="center">
            {/* Premium Avatar */}
            <Box shadowColor="#16a34a" shadowOffset={{ width: 0, height: 4 }} shadowOpacity={0.2} shadowRadius={8} elevation={4} borderRadius="$full">
              <LinearGradient colors={['#22c55e', '#16a34a']} style={{ padding: 3, borderRadius: 100 }}>
                <Avatar bgColor="$white" size="xl" borderRadius="$full">
                  <AvatarFallbackText color="$green600">{initials}</AvatarFallbackText>
                </Avatar>
              </LinearGradient>
            </Box>

            <VStack flex={1}>
              <Text size="xl" bold color="$coolGray900">{user?.full_name || "Guest User"}</Text>
              <Text size="sm" color="$coolGray500">{user?.email || "guest@plateplanner.com"}</Text>
              <Box mt="$2" alignSelf="flex-start" px="$3" py="$1" bg={user?.is_premium ? "$green100" : "$coolGray100"} borderRadius="$full">
                <Text size="xs" color={user?.is_premium ? "$green700" : "$coolGray600"} bold>
                  {user?.is_premium ? "Pro Member" : "Free Plan"}
                </Text>
              </Box>
            </VStack>
          </HStack>
        </Box>

        {/* Dietary Presets Section */}
        <Box px="$6" mb="$6">
          <HStack alignItems="center" justifyContent="space-between" mb="$4">
            <Text size="lg" bold color="$coolGray900">Dietary Preferences</Text>
            {savingPrefs && <ActivityIndicator size="small" color="#16a34a" />}
          </HStack>

          {loadingPrefs ? (
            <Box alignItems="center" py="$6">
              <ActivityIndicator size="large" color="#16a34a" />
            </Box>
          ) : (
            <VStack space="md" bg="$white" p="$5" borderRadius="$2xl" shadowColor="$black" shadowOffset={{ width: 0, height: 2 }} shadowOpacity={0.05} shadowRadius={8} elevation={2} borderWidth={1} borderColor="$coolGray100">

              <HStack justifyContent="space-between" alignItems="center">
                <HStack space="sm" alignItems="center">
                  <Box w={8} h={8} bg="$green100" borderRadius="$full" alignItems="center" justifyContent="center">
                    <Text size="xs">🌱</Text>
                  </Box>
                  <VStack>
                    <Text color="$coolGray800" bold>Vegan</Text>
                    <Text color="$coolGray400" size="xs">No animal products</Text>
                  </VStack>
                </HStack>
                <Switch value={preferences.vegan} onValueChange={() => togglePreference('vegan')} trackColor={{ false: '#e5e7eb', true: '#22c55e' }} />
              </HStack>

              <Divider my="$1" bg="$coolGray100" />

              <HStack justifyContent="space-between" alignItems="center">
                <HStack space="sm" alignItems="center">
                  <Box w={8} h={8} bg="$green50" borderRadius="$full" alignItems="center" justifyContent="center">
                    <Text size="xs">🥗</Text>
                  </Box>
                  <VStack>
                    <Text color="$coolGray800" bold>Vegetarian</Text>
                    <Text color="$coolGray400" size="xs">No meat or fish</Text>
                  </VStack>
                </HStack>
                <Switch value={preferences.vegetarian} onValueChange={() => togglePreference('vegetarian')} trackColor={{ false: '#e5e7eb', true: '#22c55e' }} />
              </HStack>

              <Divider my="$1" bg="$coolGray100" />

              <HStack justifyContent="space-between" alignItems="center">
                <HStack space="sm" alignItems="center">
                  <Box w={8} h={8} bg="$blue100" borderRadius="$full" alignItems="center" justifyContent="center">
                    <Text size="xs">🚫</Text>
                  </Box>
                  <VStack>
                    <Text color="$coolGray800" bold>Gluten-Free</Text>
                    <Text color="$coolGray400" size="xs">Exclude wheat & grains</Text>
                  </VStack>
                </HStack>
                <Switch value={preferences.glutenFree} onValueChange={() => togglePreference('glutenFree')} trackColor={{ false: '#e5e7eb', true: '#22c55e' }} />
              </HStack>

              <Divider my="$1" bg="$coolGray100" />

              <HStack justifyContent="space-between" alignItems="center">
                <HStack space="sm" alignItems="center">
                  <Box w={8} h={8} bg="$purple100" borderRadius="$full" alignItems="center" justifyContent="center">
                    <Text size="xs">🥛</Text>
                  </Box>
                  <VStack>
                    <Text color="$coolGray800" bold>Dairy-Free</Text>
                    <Text color="$coolGray400" size="xs">No milk, cheese or butter</Text>
                  </VStack>
                </HStack>
                <Switch value={preferences.dairyFree} onValueChange={() => togglePreference('dairyFree')} trackColor={{ false: '#e5e7eb', true: '#22c55e' }} />
              </HStack>

              <Divider my="$1" bg="$coolGray100" />

              <HStack justifyContent="space-between" alignItems="center">
                <HStack space="sm" alignItems="center">
                  <Box w={8} h={8} bg="$orange100" borderRadius="$full" alignItems="center" justifyContent="center">
                    <Text size="xs">🥩</Text>
                  </Box>
                  <VStack>
                    <Text color="$coolGray800" bold>Keto (Low-Carb)</Text>
                    <Text color="$coolGray400" size="xs">High fat, low carbohydrate</Text>
                  </VStack>
                </HStack>
                <Switch value={preferences.keto} onValueChange={() => togglePreference('keto')} trackColor={{ false: '#e5e7eb', true: '#22c55e' }} />
              </HStack>

            </VStack>
          )}
        </Box>

        {/* Cuisine Preferences Section */}
        <Box px="$6" mb="$6">
          <Text size="lg" bold color="$coolGray900" mb="$4">Cuisine Preferences</Text>
          <Box bg="$white" p="$5" borderRadius="$2xl" shadowColor="$black" shadowOffset={{ width: 0, height: 2 }} shadowOpacity={0.05} shadowRadius={8} elevation={2} borderWidth={1} borderColor="$coolGray100">
            <Text color="$coolGray500" size="sm" mb="$3">
              Select your favorite cuisines for personalized recipe suggestions
            </Text>
            <HStack flexWrap="wrap" style={{ gap: 8 }}>
              {CUISINE_OPTIONS.map((cuisine) => {
                const selected = cuisinePrefs.includes(cuisine);
                return (
                  <TouchableOpacity key={cuisine} onPress={() => toggleCuisine(cuisine)} activeOpacity={0.7}>
                    <Box
                      px="$3"
                      py="$2"
                      borderRadius="$full"
                      borderWidth={1.5}
                      borderColor={selected ? "$green600" : "$coolGray200"}
                      bg={selected ? "$green50" : "transparent"}
                    >
                      <Text size="sm" color={selected ? "$green700" : "$coolGray600"} bold={selected}>
                        {cuisine}
                      </Text>
                    </Box>
                  </TouchableOpacity>
                );
              })}
            </HStack>
          </Box>
        </Box>

        {/* Allergies Section */}
        <Box px="$6" mb="$8">
          <Text size="lg" bold color="$coolGray900" mb="$4">Allergies</Text>
          <Box bg="$white" p="$5" borderRadius="$2xl" shadowColor="$black" shadowOffset={{ width: 0, height: 2 }} shadowOpacity={0.05} shadowRadius={8} elevation={2} borderWidth={1} borderColor="$coolGray100">
            <Text color="$coolGray500" size="sm" mb="$3">
              Select allergens to exclude from recipes and meal plans
            </Text>
            <HStack flexWrap="wrap" style={{ gap: 8 }}>
              {ALLERGY_OPTIONS.map((allergy) => {
                const selected = allergies.includes(allergy);
                return (
                  <TouchableOpacity key={allergy} onPress={() => toggleAllergy(allergy)} activeOpacity={0.7}>
                    <Box
                      px="$3"
                      py="$2"
                      borderRadius="$full"
                      borderWidth={1.5}
                      borderColor={selected ? "$red500" : "$coolGray200"}
                      bg={selected ? "$red50" : "transparent"}
                    >
                      <Text size="sm" color={selected ? "$red600" : "$coolGray600"} bold={selected}>
                        {allergy}
                      </Text>
                    </Box>
                  </TouchableOpacity>
                );
              })}
            </HStack>
          </Box>
        </Box>

        {/* Account Settings */}
        <Box px="$6" mb="$8">
          <Text size="lg" bold color="$coolGray900" mb="$4">Account</Text>

          <VStack bg="$white" borderRadius="$2xl" shadowColor="$black" shadowOffset={{ width: 0, height: 2 }} shadowOpacity={0.05} shadowRadius={8} elevation={2} borderWidth={1} borderColor="$coolGray100">

            <TouchableOpacity onPress={() => router.push('/nutrition-goals')} activeOpacity={0.7}>
              <HStack
                justifyContent="space-between"
                alignItems="center"
                p="$4"
                borderBottomWidth={1}
                borderBottomColor="$coolGray100"
              >
                <HStack space="sm" alignItems="center">
                  <Text size="md">🎯</Text>
                  <Text color="$coolGray700" bold>Nutrition Goals</Text>
                </HStack>
                <Icon as={ChevronRightIcon} color="$coolGray400" />
              </HStack>
            </TouchableOpacity>

            <TouchableOpacity onPress={() => router.push('/progress')} activeOpacity={0.7}>
              <HStack justifyContent="space-between" alignItems="center" p="$4" borderBottomWidth={1} borderBottomColor="$coolGray100">
                <HStack space="sm" alignItems="center">
                  <Text size="md">📊</Text>
                  <Text color="$coolGray700" bold>Progress & Stats</Text>
                </HStack>
                <Icon as={ChevronRightIcon} color="$coolGray400" />
              </HStack>
            </TouchableOpacity>

            <TouchableOpacity onPress={() => router.push('/insights')} activeOpacity={0.7}>
              <HStack justifyContent="space-between" alignItems="center" p="$4">
                <HStack space="sm" alignItems="center">
                  <Text size="md">💡</Text>
                  <Text color="$coolGray700" bold>Nutrition Insights</Text>
                </HStack>
                <Icon as={ChevronRightIcon} color="$coolGray400" />
              </HStack>
            </TouchableOpacity>

          </VStack>
        </Box>

        {/* Logout */}
        <Box px="$6" mb="$10">
          <Button variant="outline" borderColor="$red200" bg="$red50" h="$12" borderRadius="$xl" onPress={handleLogout}>
            <Icon as={LogOut} color="$red500" mr="$2" />
            <ButtonText color="$red600" bold>Sign Out</ButtonText>
          </Button>
        </Box>

      </ScrollView>
    </SafeAreaView>
  );
}
