import {
  ScrollView,
  ActivityIndicator,
  Modal,
  TextInput,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  Alert,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import {
  Box,
  Text,
  VStack,
  HStack,
  Button,
  ButtonText,
  Divider,
  Pressable,
} from "@gluestack-ui/themed";
import { useState, useEffect, useCallback } from "react";
import { useRouter } from "expo-router";
import { useFocusEffect } from "@react-navigation/native";
import { useAuth } from "../src/state/auth";
import { apiRequest } from "../src/api/client";

type MealLogItem = {
  id: string;
  log_date: string;
  meal_type: string;
  description: string;
  calories: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  source: string;
  image_url: string | null;
};

type DailyLog = {
  date: string;
  meals: MealLogItem[];
  totals: { calories: number; protein_g: number; carbs_g: number; fat_g: number };
};

type TodaySummary = {
  consumed: { calories: number; protein_g: number; carbs_g: number; fat_g: number; meals_count: number };
  targets: { calories: number; protein_g: number; carbs_g: number; fat_g: number };
};

const MEAL_TYPES = ["Breakfast", "Lunch", "Dinner", "Snack"];

const MEAL_ICONS: Record<string, string> = {
  Breakfast: "🌅",
  Lunch: "☀️",
  Dinner: "🌙",
  Snack: "🍎",
};

function formatDate(d: Date): string {
  return d.toISOString().split("T")[0];
}

export default function MealLogScreen() {
  const router = useRouter();
  const { token } = useAuth();
  const today = formatDate(new Date());

  const [selectedDate, setSelectedDate] = useState(today);
  const [dailyLog, setDailyLog] = useState<DailyLog | null>(null);
  const [todaySummary, setTodaySummary] = useState<TodaySummary | null>(null);
  const [loading, setLoading] = useState(false);

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [modalMealType, setModalMealType] = useState("Breakfast");
  const [modalDescription, setModalDescription] = useState("");
  const [logging, setLogging] = useState(false);
  const [lastAiResult, setLastAiResult] = useState<MealLogItem | null>(null);

  const fetchLog = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await apiRequest<DailyLog>(`/nutrition/log/daily?date=${selectedDate}`, { token });
      setDailyLog(data);
    } catch (e: any) {
      console.log("Failed to fetch daily log:", e?.message);
    } finally {
      setLoading(false);
    }
  }, [token, selectedDate]);

  const fetchTodaySummary = useCallback(async () => {
    if (!token) return;
    try {
      const data = await apiRequest<TodaySummary>("/nutrition/log/today-summary", { token });
      setTodaySummary(data);
    } catch (e: any) {
      console.log("Failed to fetch today summary:", e?.message);
    }
  }, [token]);

  useFocusEffect(
    useCallback(() => {
      fetchLog();
      if (selectedDate === today) fetchTodaySummary();
    }, [fetchLog, fetchTodaySummary, selectedDate, today])
  );

  useEffect(() => {
    fetchLog();
    if (selectedDate === today) fetchTodaySummary();
  }, [selectedDate]);

  const handleLogMeal = async () => {
    if (!modalDescription.trim() || !token) return;
    setLogging(true);
    try {
      const result = await apiRequest<MealLogItem>("/nutrition/log/meal", {
        method: "POST",
        token,
        body: {
          date: selectedDate,
          meal_type: modalMealType,
          description: modalDescription.trim(),
        },
      });
      setLastAiResult(result);
      setModalDescription("");
      setShowModal(false);
      await fetchLog();
      if (selectedDate === today) await fetchTodaySummary();
    } catch (e: any) {
      Alert.alert("Error", e?.message || "Failed to log meal. Check server.");
    } finally {
      setLogging(false);
    }
  };

  const handleDeleteMeal = (id: string, description: string) => {
    Alert.alert("Remove Meal", `Remove "${description}" from your log?`, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Remove",
        style: "destructive",
        onPress: async () => {
          try {
            await apiRequest(`/nutrition/log/meal/${id}`, { method: "DELETE", token: token! });
            await fetchLog();
            if (selectedDate === today) await fetchTodaySummary();
          } catch {
            Alert.alert("Error", "Could not delete meal.");
          }
        },
      },
    ]);
  };

  // Grouped meals by type
  const mealsByType: Record<string, MealLogItem[]> = {};
  for (const type of MEAL_TYPES) mealsByType[type] = [];
  for (const m of dailyLog?.meals || []) {
    const key = MEAL_TYPES.find(t => t.toLowerCase() === m.meal_type.toLowerCase()) || m.meal_type;
    mealsByType[key] = [...(mealsByType[key] || []), m];
  }

  const totals = dailyLog?.totals ?? { calories: 0, protein_g: 0, carbs_g: 0, fat_g: 0 };
  const targets = todaySummary?.targets ?? { calories: 2000, protein_g: 150, carbs_g: 200, fat_g: 65 };

  const calPct = Math.min((totals.calories / targets.calories) * 100, 100);

  // Date nav
  const shiftDate = (days: number) => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() + days);
    setSelectedDate(formatDate(d));
  };

  const displayDate = selectedDate === today
    ? "Today"
    : new Date(selectedDate + "T12:00:00").toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#FAFAFA" }} edges={["top", "left", "right"]}>
      {/* Header */}
      <Box px="$6" pt="$4" pb="$3" bg="$white" shadowColor="$black" shadowOffset={{ width: 0, height: 2 }} shadowOpacity={0.04} shadowRadius={4} elevation={2}>
        <HStack alignItems="center" justifyContent="space-between" mb="$3">
          <TouchableOpacity onPress={() => router.back()}>
            <Text color="$green600" bold>‹ Back</Text>
          </TouchableOpacity>
          <Text size="xl" bold color="$coolGray900">Meal Log</Text>
          <Box w={50} />
        </HStack>

        {/* Date Nav */}
        <HStack alignItems="center" justifyContent="space-between">
          <TouchableOpacity onPress={() => shiftDate(-1)}>
            <Box px="$3" py="$2"><Text color="$coolGray500" size="lg">‹</Text></Box>
          </TouchableOpacity>
          <Text bold color="$coolGray800" size="md">{displayDate}</Text>
          <TouchableOpacity onPress={() => shiftDate(1)} disabled={selectedDate >= today}>
            <Box px="$3" py="$2"><Text color={selectedDate >= today ? "$coolGray200" : "$coolGray500"} size="lg">›</Text></Box>
          </TouchableOpacity>
        </HStack>
      </Box>

      <ScrollView contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 120 }}>

        {/* Daily Summary Bar */}
        <Box bg="$white" borderRadius="$2xl" p="$4" mt="$4" mb="$4" borderWidth={1} borderColor="$coolGray100" shadowColor="$black" shadowOffset={{ width: 0, height: 2 }} shadowOpacity={0.04} shadowRadius={6}>
          <HStack justifyContent="space-between" mb="$2">
            <Text bold color="$coolGray800">Calories Today</Text>
            <Text bold color="$green600">{totals.calories} / {targets.calories} kcal</Text>
          </HStack>
          {/* Progress bar */}
          <Box h={8} bg="$coolGray100" borderRadius="$full" overflow="hidden" mb="$3">
            <Box h={8} w={`${calPct}%`} bg={calPct > 100 ? "$orange500" : "$green500"} borderRadius="$full" />
          </Box>
          <HStack justifyContent="space-between">
            {(["protein_g", "carbs_g", "fat_g"] as const).map((macro) => {
              const labels: Record<string, string> = { protein_g: "Protein", carbs_g: "Carbs", fat_g: "Fat" };
              const colors: Record<string, string> = { protein_g: "#3b82f6", carbs_g: "#f59e0b", fat_g: "#ef4444" };
              const val = totals[macro] || 0;
              const target = targets[macro] || 1;
              const pct = Math.min((val / target) * 100, 100);
              return (
                <VStack key={macro} alignItems="center" flex={1} mx="$1">
                  <Text size="xs" color="$coolGray500" mb="$1">{labels[macro]}</Text>
                  <Box h={4} w="100%" bg="$coolGray100" borderRadius="$full" overflow="hidden" mb="$1">
                    <Box h={4} w={`${pct}%`} borderRadius="$full" style={{ backgroundColor: colors[macro] }} />
                  </Box>
                  <Text size="xs" bold color="$coolGray700">{val}g</Text>
                </VStack>
              );
            })}
          </HStack>
        </Box>

        {/* Meal Sections */}
        {loading ? (
          <Box alignItems="center" py="$8">
            <ActivityIndicator size="large" color="#16a34a" />
          </Box>
        ) : (
          MEAL_TYPES.map((mealType) => (
            <Box key={mealType} mb="$4">
              <HStack alignItems="center" mb="$2">
                <Text size="sm">{MEAL_ICONS[mealType]}</Text>
                <Text bold color="$coolGray800" ml="$2">{mealType}</Text>
                {mealsByType[mealType]?.length > 0 && (
                  <Text color="$coolGray400" size="xs" ml="$2">
                    · {mealsByType[mealType].reduce((s, m) => s + (m.calories || 0), 0)} kcal
                  </Text>
                )}
              </HStack>

              <Box bg="$white" borderRadius="$xl" borderWidth={1} borderColor="$coolGray100" overflow="hidden">
                {mealsByType[mealType]?.map((meal, idx) => (
                  <Box key={meal.id}>
                    {idx > 0 && <Divider bg="$coolGray100" />}
                    <HStack alignItems="center" p="$3" justifyContent="space-between">
                      <VStack flex={1} mr="$2">
                        <Text color="$coolGray800" size="sm" numberOfLines={1}>{meal.description}</Text>
                        <HStack space="xs" mt="$1" flexWrap="wrap">
                          {meal.calories != null && (
                            <Box px="$2" py="$0.5" bg="$green100" borderRadius="$full">
                              <Text size="xs" color="$green700">{meal.calories} kcal</Text>
                            </Box>
                          )}
                          {meal.source === "ai_estimated" && (
                            <Box px="$2" py="$0.5" bg="$blue100" borderRadius="$full">
                              <Text size="xs" color="$blue700">AI</Text>
                            </Box>
                          )}
                        </HStack>
                      </VStack>
                      <TouchableOpacity onPress={() => handleDeleteMeal(meal.id, meal.description)}>
                        <Box p="$2">
                          <Text color="$red400">✕</Text>
                        </Box>
                      </TouchableOpacity>
                    </HStack>
                  </Box>
                ))}

                {/* Add meal row */}
                <TouchableOpacity onPress={() => { setModalMealType(mealType); setShowModal(true); }}>
                  <HStack alignItems="center" p="$3" space="sm">
                    <Box w={24} h={24} bg="$green100" borderRadius="$full" alignItems="center" justifyContent="center">
                      <Text color="$green700" bold>+</Text>
                    </Box>
                    <Text color="$green600" size="sm">Add {mealType}</Text>
                  </HStack>
                </TouchableOpacity>
              </Box>
            </Box>
          ))
        )}
      </ScrollView>

      {/* Floating Log Button */}
      <Box position="absolute" bottom={100} left={20} right={20}>
        <Button
          bg="$green600"
          borderRadius="$xl"
          h="$14"
          onPress={() => setShowModal(true)}
          shadowColor="$green600"
          shadowOffset={{ width: 0, height: 4 }}
          shadowOpacity={0.3}
          shadowRadius={8}
        >
          <ButtonText color="$white" bold size="md">+ Log a Meal</ButtonText>
        </Button>
      </Box>

      {/* Log Meal Modal */}
      <Modal visible={showModal} animationType="slide" transparent presentationStyle="pageSheet">
        <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
          <Box flex={1} justifyContent="flex-end">
            <Box bg="$white" borderTopLeftRadius={24} borderTopRightRadius={24} p="$6" pb="$10"
              shadowColor="$black" shadowOffset={{ width: 0, height: -4 }} shadowOpacity={0.1} shadowRadius={12}>

              {/* Handle */}
              <Box w={40} h={4} bg="$coolGray200" borderRadius="$full" alignSelf="center" mb="$6" />

              <Text size="xl" bold color="$coolGray900" mb="$5">Log a Meal</Text>

              {/* Meal type selector */}
              <Text size="sm" color="$coolGray500" mb="$2">Meal Type</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 16 }}>
                <HStack space="sm">
                  {MEAL_TYPES.map(t => (
                    <TouchableOpacity key={t} onPress={() => setModalMealType(t)}>
                      <Box
                        px="$4" py="$2" borderRadius="$full"
                        bg={modalMealType === t ? "$green600" : "$coolGray100"}
                        borderWidth={1}
                        borderColor={modalMealType === t ? "$green600" : "$coolGray200"}
                      >
                        <Text color={modalMealType === t ? "$white" : "$coolGray600"} size="sm" bold={modalMealType === t}>
                          {MEAL_ICONS[t]} {t}
                        </Text>
                      </Box>
                    </TouchableOpacity>
                  ))}
                </HStack>
              </ScrollView>

              {/* Description input */}
              <Text size="sm" color="$coolGray500" mb="$2">Describe your meal</Text>
              <TextInput
                placeholder="e.g. 2 scrambled eggs with toast and orange juice"
                placeholderTextColor="#9ca3af"
                value={modalDescription}
                onChangeText={setModalDescription}
                multiline
                numberOfLines={3}
                style={{
                  borderWidth: 1,
                  borderColor: "#e5e7eb",
                  borderRadius: 12,
                  padding: 14,
                  fontSize: 15,
                  color: "#111827",
                  marginBottom: 8,
                  textAlignVertical: "top",
                  minHeight: 80,
                  backgroundColor: "#f9fafb",
                }}
              />
              <Text size="xs" color="$coolGray400" mb="$5">
                🤖 AI will estimate calories if you don't provide them
              </Text>

              {/* Buttons */}
              <HStack space="md">
                <Button flex={1} variant="outline" borderColor="$coolGray300" borderRadius="$xl" onPress={() => { setShowModal(false); setModalDescription(""); }}>
                  <ButtonText color="$coolGray600">Cancel</ButtonText>
                </Button>
                <Button
                  flex={2}
                  bg="$green600"
                  borderRadius="$xl"
                  onPress={handleLogMeal}
                  disabled={logging || !modalDescription.trim()}
                  opacity={!modalDescription.trim() ? 0.5 : 1}
                >
                  {logging ? (
                    <ActivityIndicator size="small" color="white" />
                  ) : (
                    <ButtonText color="$white" bold>Log Meal</ButtonText>
                  )}
                </Button>
              </HStack>
            </Box>
          </Box>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}
