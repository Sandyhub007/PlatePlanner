import React, { useState, useEffect, useCallback } from "react";
import {
  ScrollView,
  Pressable,
  ActivityIndicator,
  Image,
  Alert,
  Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import {
  Box,
  Text,
  VStack,
  HStack,
  Input,
  InputField,
  Icon,
  Avatar,
  AvatarFallbackText,
  AvatarImage,
  Button,
  ButtonText,
  Modal,
  ModalBackdrop,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  ModalFooter,
  Heading,
} from "@gluestack-ui/themed";
import {
  ChevronRight,
  LogOut,
  Mail,
  User,
  Camera,
  Shield,
  Utensils,
  AlertCircle,
  Clock,
  Users,
  DollarSign,
  Target,
  Pencil,
  Check,
  X,
} from "lucide-react-native";
import { useAuth } from "../../src/state/auth";
import { apiRequest } from "../../src/api/client";
import type { User as UserType, UserPreferences } from "../../src/api/types";

export default function ProfileScreen() {
  const { user, token, logout } = useAuth();
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [editingName, setEditingName] = useState(false);
  const [nameValue, setNameValue] = useState(user?.full_name || "");
  const [savingName, setSavingName] = useState(false);

  // Load preferences
  useEffect(() => {
    if (!token) return;
    const loadPreferences = async () => {
      try {
        const prefs = await apiRequest<UserPreferences>("/users/me/preferences", {
          token,
        });
        setPreferences(prefs);
      } catch (e) {
        console.error("Failed to load preferences", e);
      } finally {
        setLoading(false);
      }
    };
    loadPreferences();
  }, [token]);

  useEffect(() => {
    setNameValue(user?.full_name || "");
  }, [user?.full_name]);

  const handleSaveName = async () => {
    if (!token || !nameValue.trim()) return;
    setSavingName(true);
    try {
      await apiRequest("/users/me", {
        method: "PUT",
        token,
        body: { full_name: nameValue.trim() },
      });
      setEditingName(false);
    } catch (e) {
      Alert.alert("Error", "Failed to update name");
    } finally {
      setSavingName(false);
    }
  };

  const [editingGoals, setEditingGoals] = useState(false);
  const [savingGoals, setSavingGoals] = useState(false);
  const [goalValues, setGoalValues] = useState({
    calories: "",
    protein: "",
    carbs: "",
    fats: "",
  });

  const handleSaveGoals = async () => {
    if (!token) return;
    setSavingGoals(true);
    try {
      const payload = {
        calorie_target: parseInt(goalValues.calories) || 0,
        protein_target: parseInt(goalValues.protein) || 0,
        carb_target: parseInt(goalValues.carbs) || 0,
        fat_target: parseInt(goalValues.fats) || 0,
      };

      const newPrefs = await apiRequest<UserPreferences>("/users/me/preferences", {
        method: "PUT",
        token,
        body: payload,
      });
      setPreferences(newPrefs);
      setEditingGoals(false);
    } catch (e) {
      Alert.alert("Error", "Failed to update nutrition targets");
    } finally {
      setSavingGoals(false);
    }
  };

  const handleLogout = () => {
    if (Platform.OS === "web") {
      logout();
    } else {
      Alert.alert("Log Out", "Are you sure you want to log out?", [
        { text: "Cancel", style: "cancel" },
        { text: "Log Out", style: "destructive", onPress: logout },
      ]);
    }
  };

  const initials = (user?.full_name || user?.email || "U")
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  const isGoogle = user?.auth_provider === "google";
  const memberSince = user?.created_at
    ? new Date(user.created_at).toLocaleDateString("en-US", {
      month: "long",
      year: "numeric",
    })
    : "";

  const [modalType, setModalType] = useState<"diet" | "allergy" | "cuisine" | null>(null);

  const handleSaveListPreference = async (newValues: string[]) => {
    if (!token || !modalType) return;

    // Construct payload safely merging existing preferences
    // We filter out nulls/undefined from current prefs just in case
    const payload: any = { ...preferences };
    delete payload.id;
    delete payload.user_id;
    delete payload.created_at;

    if (modalType === "diet") payload.dietary_restrictions = newValues;
    if (modalType === "allergy") payload.allergies = newValues;
    if (modalType === "cuisine") payload.cuisine_preferences = newValues;

    try {
      const newPrefs = await apiRequest<UserPreferences>("/users/me/preferences", {
        method: "PUT",
        token,
        body: payload,
      });
      setPreferences(newPrefs);
      setModalType(null);
    } catch (e) {
      console.error(e);
      Alert.alert("Error", "Failed to update preferences");
    }
  };

  if (loading) {
    return (
      <SafeAreaView
        style={{ flex: 1, backgroundColor: "#FAFAFA", justifyContent: "center", alignItems: "center" }}
        edges={["top", "left", "right"]}
      >
        <ActivityIndicator size="large" color="#16a34a" />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView
      style={{ flex: 1, backgroundColor: "#FAFAFA" }}
      edges={["top", "left", "right"]}
    >
      {/* Header */}
      <Box px="$6" py="$4">
        <Text size="xl" bold color="$coolGray900">
          Profile
        </Text>
      </Box>

      <ScrollView
        contentContainerStyle={{ padding: 24, paddingBottom: 120, gap: 20 }}
      >
        {/* Profile Card */}
        <Box
          bg="$white"
          p="$6"
          borderRadius="$2xl"
          borderWidth={1}
          borderColor="$coolGray100"
        >
          <VStack alignItems="center" space="md">
            {/* Avatar */}
            <Box position="relative">
              {user?.profile_photo_url ? (
                <Image
                  source={{ uri: user.profile_photo_url }}
                  style={{
                    width: 88,
                    height: 88,
                    borderRadius: 44,
                    borderWidth: 3,
                    borderColor: "#16a34a",
                  }}
                />
              ) : (
                <Box
                  w={88}
                  h={88}
                  borderRadius="$full"
                  bg="#16a34a"
                  alignItems="center"
                  justifyContent="center"
                  borderWidth={3}
                  borderColor="#DCFCE7"
                >
                  <Text color="$white" size="2xl" bold>
                    {initials}
                  </Text>
                </Box>
              )}
            </Box>

            {/* Name — editable */}
            {editingName ? (
              <HStack alignItems="center" space="sm">
                <Input
                  w="$56"
                  variant="outline"
                  size="md"
                  borderColor="$green300"
                >
                  <InputField
                    value={nameValue}
                    onChangeText={setNameValue}
                    placeholder="Your name"
                    autoFocus
                  />
                </Input>
                <Pressable onPress={handleSaveName} disabled={savingName}>
                  {savingName ? (
                    <ActivityIndicator size="small" color="#16a34a" />
                  ) : (
                    <Check size={20} color="#22C55E" />
                  )}
                </Pressable>
                <Pressable
                  onPress={() => {
                    setEditingName(false);
                    setNameValue(user?.full_name || "");
                  }}
                >
                  <X size={20} color="#EF4444" />
                </Pressable>
              </HStack>
            ) : (
              <Pressable onPress={() => setEditingName(true)}>
                <HStack alignItems="center" space="xs">
                  <Text size="xl" bold color="$coolGray900">
                    {user?.full_name || "Set your name"}
                  </Text>
                  <Pencil size={14} color="#9CA3AF" />
                </HStack>
              </Pressable>
            )}

            {/* Email */}
            <HStack alignItems="center" space="xs">
              <Mail size={14} color="#9CA3AF" />
              <Text size="sm" color="$coolGray500">
                {user?.email}
              </Text>
            </HStack>

            {/* Auth Provider Badge */}
            {isGoogle ? (
              <Box
                bg="#EEF2FF"
                px="$3"
                py="$1.5"
                borderRadius="$full"
                flexDirection="row"
                alignItems="center"
              >
                <Image
                  source={{
                    uri: "https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg",
                  }}
                  style={{ width: 16, height: 16, marginRight: 6 }}
                />
                <Text size="xs" color="#4338CA" bold>
                  Signed in with Google
                </Text>
              </Box>
            ) : (
              <Box
                bg="#F0FDF4"
                px="$3"
                py="$1.5"
                borderRadius="$full"
                flexDirection="row"
                alignItems="center"
              >
                <Mail size={12} color="#16A34A" style={{ marginRight: 6 }} />
                <Text size="xs" color="#16A34A" bold>
                  Email &amp; Password
                </Text>
              </Box>
            )}

            {/* Member Since */}
            {memberSince ? (
              <Text size="xs" color="$coolGray400">
                Member since {memberSince}
              </Text>
            ) : null}
          </VStack>
        </Box>

        {/* Dietary Preferences Section */}
        <Box>
          <Text
            size="xs"
            color="$coolGray500"
            bold
            mb="$2"
            textTransform="uppercase"
            letterSpacing="$lg"
          >
            Dietary Preferences
          </Text>
          <Box
            bg="$white"
            px="$4"
            borderRadius="$2xl"
            borderWidth={1}
            borderColor="$coolGray100"
          >
            <PreferenceRow
              icon={<Utensils size={18} color="#16a34a" />}
              title="Dietary Restrictions"
              value={
                preferences?.dietary_restrictions?.length
                  ? preferences.dietary_restrictions.join(", ")
                  : "None set"
              }
              onPress={() => setModalType("diet")}
            />
            <PreferenceRow
              icon={<AlertCircle size={18} color="#EF4444" />}
              title="Allergies"
              value={
                preferences?.allergies?.length
                  ? preferences.allergies.join(", ")
                  : "None"
              }
              onPress={() => setModalType("allergy")}
            />
            <PreferenceRow
              icon={<Utensils size={18} color="#8B5CF6" />}
              title="Cuisine Preferences"
              value={
                preferences?.cuisine_preferences?.length
                  ? preferences.cuisine_preferences.join(", ")
                  : "Any"
              }
              isLast
              onPress={() => setModalType("cuisine")}
            />
          </Box>
        </Box>

        {/* Nutrition Targets */}
        <Box>
          <HStack justifyContent="space-between" alignItems="center" mb="$2">
            <Text
              size="xs"
              color="$coolGray500"
              bold
              textTransform="uppercase"
              letterSpacing="$lg"
            >
              Nutrition Targets
            </Text>
            {!editingGoals ? (
              <Pressable onPress={() => {
                setGoalValues({
                  calories: String(preferences?.calorie_target || 2000),
                  protein: String(preferences?.protein_target || 150),
                  carbs: String(preferences?.carb_target || 250),
                  fats: String(preferences?.fat_target || 70),
                });
                setEditingGoals(true);
              }}>
                <HStack space="xs" alignItems="center">
                  <Text size="xs" color="$green600" bold>Edit</Text>
                  <Pencil size={12} color="#16a34a" />
                </HStack>
              </Pressable>
            ) : (
              <HStack space="md">
                <Pressable onPress={() => setEditingGoals(false)}>
                  <Text size="xs" color="$coolGray500" bold>Cancel</Text>
                </Pressable>
                <Pressable onPress={handleSaveGoals}>
                  {savingGoals ? <ActivityIndicator size="small" color="#16a34a" /> : <Text size="xs" color="$green600" bold>Save</Text>}
                </Pressable>
              </HStack>
            )}
          </HStack>

          {editingGoals ? (
            <VStack space="sm" bg="$white" p="$4" borderRadius="$2xl" borderWidth={1} borderColor="$coolGray100">
              <HStack space="md">
                <VStack flex={1}>
                  <Text size="xs" color="$coolGray500" mb={4}>Calories (kcal)</Text>
                  <Input variant="outline" size="sm" borderColor="$coolGray200" borderRadius={8}>
                    <InputField keyboardType="numeric" value={goalValues.calories} onChangeText={(t) => setGoalValues(prev => ({ ...prev, calories: t }))} />
                  </Input>
                </VStack>
                <VStack flex={1}>
                  <Text size="xs" color="$coolGray500" mb={4}>Protein (g)</Text>
                  <Input variant="outline" size="sm" borderColor="$coolGray200" borderRadius={8}>
                    <InputField keyboardType="numeric" value={goalValues.protein} onChangeText={(t) => setGoalValues(prev => ({ ...prev, protein: t }))} />
                  </Input>
                </VStack>
              </HStack>
              <HStack space="md">
                <VStack flex={1}>
                  <Text size="xs" color="$coolGray500" mb={4}>Carbs (g)</Text>
                  <Input variant="outline" size="sm" borderColor="$coolGray200" borderRadius={8}>
                    <InputField keyboardType="numeric" value={goalValues.carbs} onChangeText={(t) => setGoalValues(prev => ({ ...prev, carbs: t }))} />
                  </Input>
                </VStack>
                <VStack flex={1}>
                  <Text size="xs" color="$coolGray500" mb={4}>Fats (g)</Text>
                  <Input variant="outline" size="sm" borderColor="$coolGray200" borderRadius={8}>
                    <InputField keyboardType="numeric" value={goalValues.fats} onChangeText={(t) => setGoalValues(prev => ({ ...prev, fats: t }))} />
                  </Input>
                </VStack>
              </HStack>
            </VStack>
          ) : (
            <HStack space="sm" flexWrap="wrap">
              <NutrientCard
                label="Calories"
                value={preferences?.calorie_target}
                unit="kcal"
                color="#16a34a"
              />
              <NutrientCard
                label="Protein"
                value={preferences?.protein_target}
                unit="g"
                color="#22C55E"
              />
              <NutrientCard
                label="Carbs"
                value={preferences?.carb_target}
                unit="g"
                color="#3B82F6"
              />
              <NutrientCard
                label="Fat"
                value={preferences?.fat_target}
                unit="g"
                color="#F59E0B"
              />
            </HStack>
          )}
        </Box>

        {/* Other Settings */}
        <Box>
          <Text
            size="xs"
            color="$coolGray500"
            bold
            mb="$2"
            textTransform="uppercase"
            letterSpacing="$lg"
          >
            Other Settings
          </Text>
          <Box
            bg="$white"
            px="$4"
            borderRadius="$2xl"
            borderWidth={1}
            borderColor="$coolGray100"
          >
            <PreferenceRow
              icon={<Clock size={18} color="#6366F1" />}
              title="Max Cooking Time"
              value={
                preferences?.cooking_time_max
                  ? `${preferences.cooking_time_max} min`
                  : "No limit"
              }
            />
            <PreferenceRow
              icon={<DollarSign size={18} color="#10B981" />}
              title="Weekly Budget"
              value={
                preferences?.budget_per_week
                  ? `$${preferences.budget_per_week}`
                  : "No limit"
              }
            />
            <PreferenceRow
              icon={<Users size={18} color="#F59E0B" />}
              title="Servings"
              value={`${preferences?.people_count || 1} ${(preferences?.people_count || 1) === 1 ? "person" : "people"
                }`}
              isLast
            />
          </Box>
        </Box>

        {/* Account Info */}
        <Box>
          <Text
            size="xs"
            color="$coolGray500"
            bold
            mb="$2"
            textTransform="uppercase"
            letterSpacing="$lg"
          >
            Account
          </Text>
          <Box
            bg="$white"
            px="$4"
            borderRadius="$2xl"
            borderWidth={1}
            borderColor="$coolGray100"
          >
            <PreferenceRow
              icon={<Shield size={18} color="#6366F1" />}
              title="Account Type"
              value={user?.is_premium ? "Premium" : "Free"}
            />
            <PreferenceRow
              icon={<User size={18} color="#9CA3AF" />}
              title="Sign-in Method"
              value={isGoogle ? "Google" : "Email"}
              isLast
            />
          </Box>
        </Box>

        {/* Log Out Button */}
        <Pressable
          onPress={handleLogout}
          style={({ pressed }) => ({
            backgroundColor: pressed ? "#FEE2E2" : "#FFF5F5",
            borderRadius: 16,
            padding: 16,
            flexDirection: "row",
            alignItems: "center",
            justifyContent: "center",
            borderWidth: 1,
            borderColor: "#FECACA",
            marginTop: 4,
          })}
        >
          <LogOut size={18} color="#EF4444" style={{ marginRight: 8 }} />
          <Text color="#EF4444" bold size="md">
            Log Out
          </Text>
        </Pressable>

        {/* Preference Modal */}
        <SelectionModal
          isOpen={!!modalType}
          onClose={() => setModalType(null)}
          title={
            modalType === "diet" ? "Dietary Restrictions" :
              modalType === "allergy" ? "Select Allergies" :
                "Cuisine Preferences"
          }
          options={
            modalType === "diet" ? DIETARY_OPTIONS :
              modalType === "allergy" ? ALLERGY_OPTIONS :
                CUISINE_OPTIONS
          }
          selectedValues={
            (modalType === "diet" ? preferences?.dietary_restrictions :
              modalType === "allergy" ? preferences?.allergies :
                preferences?.cuisine_preferences) || []
          }
          onSave={(vals) => modalType && handleSaveListPreference(vals)}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const DIETARY_OPTIONS = ["Vegan", "Vegetarian", "Pescatarian", "Keto", "Paleo", "Gluten-Free", "Dairy-Free", "Low-Carb", "Whole30"];
const ALLERGY_OPTIONS = ["Peanuts", "Tree Nuts", "Milk", "Eggs", "Wheat", "Soy", "Fish", "Shellfish", "Sesame"];
const CUISINE_OPTIONS = ["Italian", "Mexican", "Chinese", "Japanese", "Indian", "Thai", "Mediterranean", "American", "French", "Greek"];

/* ————— Sub-Components ————— */

function PreferenceRow({
  icon,
  title,
  value,
  isLast,
  onPress,
}: {
  icon: React.ReactNode;
  title: string;
  value: string;
  isLast?: boolean;
  onPress?: () => void;
}) {
  return (
    <Pressable onPress={onPress}>
      <HStack
        justifyContent="space-between"
        alignItems="center"
        py="$4"
        borderBottomWidth={isLast ? 0 : 1}
        borderColor="$coolGray50"
      >
        <HStack alignItems="center" space="sm">
          {icon}
          <Text color="$coolGray900" size="md">
            {title}
          </Text>
        </HStack>
        <HStack alignItems="center" space="xs">
          <Text color="$coolGray500" size="sm" numberOfLines={1} maxWidth={150}>
            {value}
          </Text>
          {onPress && <ChevronRight size={16} color="#D1D5DB" />}
        </HStack>
      </HStack>
    </Pressable>
  );
}

function NutrientCard({
  label,
  value,
  unit,
  color,
}: {
  label: string;
  value?: number | null;
  unit: string;
  color: string;
}) {
  return (
    <Box
      bg="$white"
      p="$4"
      borderRadius="$2xl"
      borderWidth={1}
      borderColor="$coolGray100"
      alignItems="center"
      minWidth={80}
      flex={1}
    >
      <Text size="xl" bold color={color}>
        {value ?? "—"}
      </Text>
      <Text size="xs" color="$coolGray400">
        {unit}
      </Text>
      <Text size="xs" color="$coolGray500" bold mt="$1">
        {label}
      </Text>
    </Box>
  );
}

/* Reusable Multi-Select Modal */
function SelectionModal({
  isOpen,
  onClose,
  title,
  options,
  selectedValues,
  onSave,
}: {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  options: string[];
  selectedValues: string[];
  onSave: (newValues: string[]) => void;
}) {
  const [localSelection, setLocalSelection] = useState<string[]>([]);

  useEffect(() => {
    if (isOpen) {
      setLocalSelection([...selectedValues]);
    }
  }, [isOpen, selectedValues]);

  const toggleOption = (option: string) => {
    if (localSelection.includes(option)) {
      setLocalSelection(localSelection.filter((item) => item !== option));
    } else {
      setLocalSelection([...localSelection, option]);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <ModalBackdrop />
      <ModalContent bg="white" p="$6" borderRadius="$2xl" maxHeight="80%">
        <ModalHeader>
          <Heading size="lg">{title}</Heading>
          <ModalCloseButton>
            <Icon as={X} />
          </ModalCloseButton>
        </ModalHeader>
        <ModalBody py="$4">
          <ScrollView showsVerticalScrollIndicator={false}>
            <VStack space="sm">
              {options.map((option) => {
                const isSelected = localSelection.includes(option);
                return (
                  <Pressable key={option} onPress={() => toggleOption(option)}>
                    <Box
                      p="$3"
                      borderRadius="$xl"
                      bg={isSelected ? "$green50" : "$coolGray50"}
                      borderWidth={1}
                      borderColor={isSelected ? "$green500" : "$coolGray100"}
                      flexDirection="row"
                      alignItems="center"
                      justifyContent="space-between"
                    >
                      <Text
                        color={isSelected ? "$green700" : "$coolGray700"}
                        bold={isSelected}
                      >
                        {option}
                      </Text>
                      {isSelected && <Check size={18} color="#16a34a" />}
                    </Box>
                  </Pressable>
                );
              })}
            </VStack>
          </ScrollView>
        </ModalBody>
        <ModalFooter>
          <Button
            variant="outline"
            action="secondary"
            mr="$3"
            onPress={onClose}
            borderColor="$coolGray200"
            borderRadius="$xl"
          >
            <ButtonText color="$coolGray600">Cancel</ButtonText>
          </Button>
          <Button
            size="md"
            bg="$green600"
            borderRadius="$xl"
            onPress={() => onSave(localSelection)}
          >
            <ButtonText color="white" bold>Save Selection</ButtonText>
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}
