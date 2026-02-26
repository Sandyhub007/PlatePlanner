import { ScrollView, Switch } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Box, Text, VStack, HStack, Avatar, AvatarFallbackText, Icon, SettingsIcon, LogOutIcon, ChevronRightIcon, Button, ButtonText, Divider } from "@gluestack-ui/themed";
import { LinearGradient } from "expo-linear-gradient";
import { useAuth } from "../../src/state/auth";
import { useState } from "react";
import { useRouter } from "expo-router";

export default function ProfileScreen() {
  const { user, signOut } = useAuth();
  const router = useRouter();

  // Dietary Preferences State (dummy state for now)
  const [preferences, setPreferences] = useState({
    vegan: false,
    vegetarian: false,
    glutenFree: true,
    dairyFree: false,
    keto: false,
    lowCarb: false,
  });

  const togglePreference = (key: keyof typeof preferences) => {
    setPreferences(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const initials = user?.full_name
    ? user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : "U";

  const handleLogout = async () => {
    await signOut();
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
              <Box mt="$2" alignSelf="flex-start" px="$3" py="$1" bg="$green100" borderRadius="$full">
                <Text size="xs" color="$green700" bold>Pro Member</Text>
              </Box>
            </VStack>
          </HStack>
        </Box>

        {/* Dietary Presets Section */}
        <Box px="$6" mb="$8">
          <Text size="lg" bold color="$coolGray900" mb="$4">Dietary Preferences</Text>

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
        </Box>

        {/* Account Settings */}
        <Box px="$6" mb="$8">
          <Text size="lg" bold color="$coolGray900" mb="$4">Account</Text>

          <VStack bg="$white" borderRadius="$2xl" shadowColor="$black" shadowOffset={{ width: 0, height: 2 }} shadowOpacity={0.05} shadowRadius={8} elevation={2} borderWidth={1} borderColor="$coolGray100">

            <HStack justifyContent="space-between" alignItems="center" p="$4" borderBottomWidth={1} borderBottomColor="$coolGray100">
              <Text color="$coolGray700">Personal Information</Text>
              <Icon as={ChevronRightIcon} color="$coolGray400" />
            </HStack>

            <HStack justifyContent="space-between" alignItems="center" p="$4" borderBottomWidth={1} borderBottomColor="$coolGray100">
              <Text color="$coolGray700">Notifications</Text>
              <Icon as={ChevronRightIcon} color="$coolGray400" />
            </HStack>

            <HStack justifyContent="space-between" alignItems="center" p="$4">
              <Text color="$coolGray700">Privacy & Security</Text>
              <Icon as={ChevronRightIcon} color="$coolGray400" />
            </HStack>

          </VStack>
        </Box>

        {/* Logout */}
        <Box px="$6" mb="$10">
          <Button variant="outline" borderColor="$red200" bg="$red50" h="$12" borderRadius="$xl" onPress={handleLogout}>
            <Icon as={LogOutIcon} color="$red500" mr="$2" />
            <ButtonText color="$red600" bold>Sign Out</ButtonText>
          </Button>
        </Box>

      </ScrollView>
    </SafeAreaView>
  );
}
