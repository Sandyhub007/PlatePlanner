import {
  ScrollView,
  TouchableOpacity,
  ImageBackground,
  View,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import {
  Box,
  Text,
  VStack,
  HStack,
  Icon,
  AddIcon,
  CalendarDaysIcon,
} from "@gluestack-ui/themed";
import { useState, useCallback } from "react";
import { useRouter } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import * as ImagePicker from "expo-image-picker";
import * as Haptics from "expo-haptics";
import { useAuth } from "../../src/state/auth";
import { apiRequest, apiUploadRequest } from "../../src/api/client";
import { useFocusEffect } from "expo-router";
import DraggableFlatList, {
  ScaleDecorator,
  RenderItemParams,
} from "react-native-draggable-flatlist";

// ── Types ────────────────────────────────────────────────────────────────────
type MealPlanItem = {
  id: string;
  plan_id: string;
  day_of_week: number;
  meal_type: string;
  recipe_id: string;
  recipe_title: string;
  servings: number;
  calories?: number | null;
  protein?: number | null;
  carbs?: number | null;
  fat?: number | null;
  estimated_cost?: number | null;
  prep_time_minutes?: number | null;
  created_at: string;
};

type MealPlan = {
  id: string;
  user_id: string;
  week_start_date: string;
  week_end_date: string;
  status: string;
  total_calories: number;
  total_protein: number;
  total_carbs: number;
  total_fat: number;
  total_estimated_cost: number;
  items: MealPlanItem[];
  created_at: string;
  updated_at: string;
};

// UI display type for the draggable list
type MealSlot = {
  key: string;
  type: string;
  filled: boolean;
  title?: string;
  image?: string;
  calories?: number;
  itemId?: string; // backend item id for delete
};

const MEAL_TYPES = ["Breakfast", "Lunch", "Dinner", "Snacks"];

// Generate this week's dates
const generateWeek = () => {
  const dates = [];
  const now = new Date();
  const dayOfWeek = now.getDay();
  for (let i = 0; i < 7; i++) {
    const day = new Date(now);
    day.setDate(now.getDate() - dayOfWeek + i);
    dates.push({
      date: day.getDate(),
      day: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][day.getDay()],
      fullDate: day.toISOString().split("T")[0],
      dayOfWeek: day.getDay(),
      isToday:
        day.getDate() === now.getDate() &&
        day.getMonth() === now.getMonth(),
    });
  }
  return dates;
};

function getWeekStart(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  const day = d.getDay();
  d.setDate(d.getDate() - day);
  return d.toISOString().split("T")[0];
}

// ── Meal Card ────────────────────────────────────────────────────────────────
function MealCard({
  meal,
  onPickImage,
  onDelete,
  drag,
  isActive,
}: {
  meal: MealSlot;
  onPickImage: (key: string) => void;
  onDelete: (key: string) => void;
  drag: () => void;
  isActive: boolean;
}) {
  return (
    <ScaleDecorator>
      <Box
        mb="$4"
        opacity={isActive ? 0.9 : 1}
        style={{
          transform: [{ scale: isActive ? 1.02 : 1 }],
          shadowColor: isActive ? "#16a34a" : "#000",
          shadowOffset: { width: 0, height: isActive ? 12 : 4 },
          shadowOpacity: isActive ? 0.25 : 0.06,
          shadowRadius: isActive ? 20 : 10,
          borderRadius: 20,
        }}
      >
        {/* Meal type header */}
        <HStack justifyContent="space-between" alignItems="center" mb="$3">
          <HStack alignItems="center" space="sm">
            {/* Drag handle */}
            <TouchableOpacity
              onLongPress={() => {
                Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
                drag();
              }}
              delayLongPress={150}
              style={{ padding: 4 }}
              activeOpacity={0.6}
            >
              <VStack space="xs" alignItems="center">
                {[0, 1, 2].map((i) => (
                  <HStack key={i} space="xs">
                    <Box w={3} h={3} borderRadius="$full" bg="$coolGray300" />
                    <Box w={3} h={3} borderRadius="$full" bg="$coolGray300" />
                  </HStack>
                ))}
              </VStack>
            </TouchableOpacity>
            <Text size="lg" bold color="$coolGray900">
              {meal.type}
            </Text>
          </HStack>
          <HStack space="sm" alignItems="center">
            {meal.calories != null && meal.calories > 0 && (
              <Text
                size="xs"
                color="$green600"
                bold
                bg="$green100"
                px="$2"
                py="$0.5"
                borderRadius="$full"
              >
                {meal.calories} kcal
              </Text>
            )}
            {meal.filled && meal.itemId && (
              <TouchableOpacity
                onPress={() => onDelete(meal.key)}
                hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
              >
                <Box
                  w={24}
                  h={24}
                  borderRadius="$full"
                  bg="$red50"
                  alignItems="center"
                  justifyContent="center"
                >
                  <Text size="xs" color="$red500" bold>✕</Text>
                </Box>
              </TouchableOpacity>
            )}
          </HStack>
        </HStack>

        {/* Card */}
        {meal.filled ? (
          <TouchableOpacity
            activeOpacity={0.8}
            onPress={() => onPickImage(meal.key)}
          >
            <Box
              bg="$white"
              borderRadius="$2xl"
              overflow="hidden"
              borderWidth={1}
              borderColor="$coolGray50"
            >
              {meal.image ? (
                <ImageBackground
                  source={{ uri: meal.image }}
                  style={{ height: 120, width: "100%" }}
                >
                  <LinearGradient
                    colors={["rgba(0,0,0,0)", "rgba(0,0,0,0.8)"]}
                    style={{
                      position: "absolute",
                      top: 0,
                      bottom: 0,
                      left: 0,
                      right: 0,
                    }}
                  />
                  <Box position="absolute" bottom={0} left={0} p="$4">
                    <Text color="$white" bold size="md">
                      {meal.title}
                    </Text>
                  </Box>
                </ImageBackground>
              ) : (
                <Box h={120} bg="$green50" alignItems="center" justifyContent="center" px="$4">
                  <Text color="$green800" bold size="md" textAlign="center" numberOfLines={2}>
                    {meal.title}
                  </Text>
                  <Text color="$green600" size="xs" mt="$1">Tap to add photo</Text>
                </Box>
              )}
            </Box>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            activeOpacity={0.7}
            onPress={() => {
              Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
              onPickImage(meal.key);
            }}
          >
            <Box
              bg="$white"
              borderRadius="$2xl"
              borderStyle="dashed"
              borderWidth={1.5}
              borderColor="$coolGray300"
              h={120}
              alignItems="center"
              justifyContent="center"
            >
              <Box
                bg="$green50"
                w={40}
                h={40}
                borderRadius="$full"
                alignItems="center"
                justifyContent="center"
                mb="$2"
              >
                <Icon as={AddIcon} color="$green600" />
              </Box>
              <Text color="$coolGray500" bold>
                Add {meal.type.toLowerCase()}
              </Text>
              <Text color="$coolGray400" size="xs">
                Tap to upload a photo
              </Text>
            </Box>
          </TouchableOpacity>
        )}
      </Box>
    </ScaleDecorator>
  );
}

// ── Main Screen ───────────────────────────────────────────────────────────────
export default function MealPlannerScreen() {
  const { token } = useAuth();
  const router = useRouter();
  const [weekDates] = useState(generateWeek());
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split("T")[0]
  );
  const [meals, setMeals] = useState<MealSlot[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [currentPlan, setCurrentPlan] = useState<MealPlan | null>(null);

  const fetchMealPlan = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const weekStart = getWeekStart(selectedDate);
      const plan = await apiRequest<MealPlan>(
        `/meal-plans/weekly?week_start=${weekStart}`,
        { token }
      );
      setCurrentPlan(plan);

      // Get the day_of_week for the selected date (0=Sun, 6=Sat)
      const selDate = new Date(selectedDate + "T00:00:00");
      const dayOfWeek = selDate.getDay();

      // Filter items for the selected day
      const dayItems = plan.items.filter((item) => item.day_of_week === dayOfWeek);

      // Build MealSlot array
      const slots: MealSlot[] = MEAL_TYPES.map((type) => {
        const match = dayItems.find(
          (item) => item.meal_type.toLowerCase() === type.toLowerCase()
        );
        if (match) {
          return {
            key: type,
            type,
            filled: true,
            title: match.recipe_title,
            calories: match.calories ?? undefined,
            itemId: match.id,
          };
        }
        return { key: type, type, filled: false };
      });
      setMeals(slots);
    } catch (err: any) {
      // 404 means no plan for this week — show empty slots
      setCurrentPlan(null);
      setMeals(MEAL_TYPES.map((type) => ({ key: type, type, filled: false })));
    } finally {
      setLoading(false);
    }
  }, [token, selectedDate]);

  useFocusEffect(
    useCallback(() => {
      fetchMealPlan();
    }, [fetchMealPlan])
  );

  const totalCalories = meals.reduce((s, m) => s + (m.calories ?? 0), 0);

  const handleGeneratePlan = async () => {
    if (!token) return;
    setGenerating(true);
    try {
      const weekStart = getWeekStart(selectedDate);
      await apiRequest<MealPlan>("/meal-plans/generate", {
        token,
        method: "POST",
        body: { week_start_date: weekStart },
      });
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      // Refresh to show the new plan
      await fetchMealPlan();
    } catch (err: any) {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      console.error("Failed to generate meal plan:", err?.message || err);
      alert("Failed to generate meal plan. Please try again.");
    } finally {
      setGenerating(false);
    }
  };

  const handleDeleteItem = async (mealKey: string) => {
    const slot = meals.find((m) => m.key === mealKey);
    if (!slot?.itemId || !currentPlan || !token) return;
    try {
      await apiRequest(
        `/meal-plans/${currentPlan.id}/items/${slot.itemId}`,
        { token, method: "DELETE" }
      );
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
      setMeals((prev) =>
        prev.map((m) =>
          m.key === mealKey
            ? { key: mealKey, type: mealKey, filled: false }
            : m
        )
      );
    } catch (err) {
      console.error("Failed to delete meal item:", err);
    }
  };

  const handlePickImage = async (mealKey: string) => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      allowsEditing: true,
      aspect: [16, 9],
      quality: 0.8,
    });

    if (!result.canceled && result.assets?.length > 0) {
      const asset = result.assets[0];
      const uriParts = asset.uri.split(".");
      const fileType = uriParts[uriParts.length - 1];
      const formData = new FormData();
      formData.append("file", {
        uri: asset.uri,
        name: `photo.${fileType}`,
        type: `image/${fileType}`,
      } as any);
      const meal = meals.find((m) => m.key === mealKey);
      formData.append("meal_type", meal?.type ?? mealKey);
      formData.append("meal_date", selectedDate);
      formData.append("title", meal?.title || "My Custom Meal");

      try {
        const response = await apiUploadRequest<{ image_url: string }>(
          "/user-meals/upload",
          formData,
          token
        );
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        setMeals((prev) =>
          prev.map((m) =>
            m.key === mealKey
              ? { ...m, filled: true, title: m.title || "My Custom Meal", image: response.image_url }
              : m
          )
        );
      } catch (err) {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
        console.error("Upload failed", err);
        alert("Failed to save meal photo. Please try again.");
      }
    }
  };

  const handleDragEnd = ({ data }: { data: MealSlot[] }) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setMeals(data);
  };

  const renderItem = ({ item, drag, isActive }: RenderItemParams<MealSlot>) => (
    <MealCard
      meal={item}
      onPickImage={handlePickImage}
      onDelete={handleDeleteItem}
      drag={drag}
      isActive={isActive}
    />
  );

  const noMealsPlanned = !loading && meals.every((m) => !m.filled);

  return (
    <SafeAreaView
      style={{ flex: 1, backgroundColor: "#FAFAFA" }}
      edges={["top", "left", "right"]}
    >
      {/* Header + Date selector */}
      <Box
        px="$6"
        pt="$4"
        pb="$4"
        bg="$white"
        shadowColor="$black"
        shadowOffset={{ width: 0, height: 4 }}
        shadowOpacity={0.03}
        shadowRadius={8}
        elevation={2}
        zIndex={10}
      >
        <HStack alignItems="center" justifyContent="space-between" mb="$6">
          <VStack>
            <Text
              color="$coolGray500"
              size="sm"
              bold
              textTransform="uppercase"
              letterSpacing={1}
            >
              This Week
            </Text>
            <Text size="3xl" bold color="$coolGray900">
              Meal Plan
            </Text>
          </VStack>
          <Box p="$2" bg="$green50" borderRadius="$full">
            <Icon as={CalendarDaysIcon} color="$green600" size="xl" />
          </Box>
        </HStack>

        <HStack justifyContent="space-between">
          {weekDates.map((d, i) => {
            const isSelected = d.fullDate === selectedDate;
            return (
              <TouchableOpacity
                key={i}
                onPress={() => {
                  Haptics.selectionAsync();
                  setSelectedDate(d.fullDate);
                }}
                activeOpacity={0.7}
              >
                <VStack
                  alignItems="center"
                  p="$2"
                  w={44}
                  h={65}
                  borderRadius="$full"
                  bg={
                    isSelected
                      ? "$green600"
                      : d.isToday
                        ? "$green50"
                        : "transparent"
                  }
                  shadowColor={isSelected ? "$green600" : "transparent"}
                  shadowOffset={{ width: 0, height: 4 }}
                  shadowOpacity={0.3}
                  shadowRadius={6}
                  elevation={isSelected ? 4 : 0}
                >
                  <Text
                    color={
                      isSelected
                        ? "$white"
                        : d.isToday
                          ? "$green700"
                          : "$coolGray400"
                    }
                    size="xs"
                    bold={isSelected}
                    mb="$1"
                  >
                    {d.day}
                  </Text>
                  <Text
                    color={isSelected ? "$white" : "$coolGray900"}
                    size="md"
                    bold={isSelected}
                  >
                    {d.date}
                  </Text>
                </VStack>
              </TouchableOpacity>
            );
          })}
        </HStack>
      </Box>

      {/* Loading state */}
      {loading && (
        <Box flex={1} alignItems="center" justifyContent="center">
          <ActivityIndicator size="large" color="#16a34a" />
          <Text color="$coolGray500" mt="$4">Loading meal plan...</Text>
        </Box>
      )}

      {/* Content when not loading */}
      {!loading && (
        <DraggableFlatList
          data={meals}
          keyExtractor={(item) => item.key}
          onDragEnd={handleDragEnd}
          renderItem={renderItem}
          contentContainerStyle={{ paddingHorizontal: 24, paddingTop: 16, paddingBottom: 140 }}
          ListHeaderComponent={
            <>
              {/* Log button */}
              <TouchableOpacity
                activeOpacity={0.85}
                onPress={() => {
                  Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                  router.push("/meal-log");
                }}
                style={{ marginBottom: 12 }}
              >
                <LinearGradient
                  colors={["#16a34a", "#22c55e"]}
                  style={{ borderRadius: 16, padding: 16 }}
                >
                  <HStack justifyContent="space-between" alignItems="center">
                    <VStack>
                      <Text color="$white" bold size="md">
                        Log Today's Meals
                      </Text>
                      <Text color="rgba(255,255,255,0.8)" size="sm">
                        Track calories with AI estimation
                      </Text>
                    </VStack>
                    <Box
                      w={36}
                      h={36}
                      borderRadius="$full"
                      bg="rgba(255,255,255,0.25)"
                      alignItems="center"
                      justifyContent="center"
                    >
                      <Text color="$white" bold size="lg">
                        →
                      </Text>
                    </Box>
                  </HStack>
                </LinearGradient>
              </TouchableOpacity>

              {/* Calorie summary */}
              <LinearGradient
                colors={["#D1FAE5", "#A7F3D0"]}
                style={{ borderRadius: 20, padding: 16, marginBottom: 16 }}
              >
                <HStack justifyContent="space-between" alignItems="center">
                  <VStack>
                    <Text color="$green800" bold>
                      Daily Planned Calories
                    </Text>
                    <Text color="$green700" size="sm">
                      {totalCalories > 0
                        ? `${totalCalories} kcal planned today`
                        : "No meals planned yet"}
                    </Text>
                  </VStack>
                  <VStack alignItems="center">
                    <Text color="$green800" bold size="xl">
                      {totalCalories}
                    </Text>
                    <Text color="$green700" size="xs">
                      kcal
                    </Text>
                  </VStack>
                </HStack>
              </LinearGradient>

              {/* Generate Plan button when no meals */}
              {noMealsPlanned && (
                <TouchableOpacity
                  activeOpacity={0.85}
                  onPress={handleGeneratePlan}
                  disabled={generating}
                  style={{ marginBottom: 16 }}
                >
                  <LinearGradient
                    colors={generating ? ["#9ca3af", "#6b7280"] : ["#7c3aed", "#a855f7"]}
                    style={{ borderRadius: 16, padding: 16, opacity: generating ? 0.7 : 1 }}
                  >
                    <HStack alignItems="center" justifyContent="center" space="sm">
                      {generating ? (
                        <ActivityIndicator size="small" color="white" />
                      ) : (
                        <Text color="white" size="lg">✨</Text>
                      )}
                      <Text color="white" bold size="md">
                        {generating ? "Generating..." : "Auto-Generate Meal Plan"}
                      </Text>
                    </HStack>
                  </LinearGradient>
                </TouchableOpacity>
              )}

              <HStack alignItems="center" mb="$3" space="sm">
                <Text size="xs" color="$coolGray400">
                  Long-press a meal to drag & reorder
                </Text>
              </HStack>
            </>
          }
          ListEmptyComponent={
            <Box alignItems="center" py="$10">
              <Text size="4xl" mb="$4">🍽️</Text>
              <Text size="lg" bold color="$coolGray900" mb="$2">
                No meals planned
              </Text>
              <Text color="$coolGray500" textAlign="center" px="$4">
                Tap "Auto-Generate Meal Plan" above to create a personalized plan based on your preferences.
              </Text>
            </Box>
          }
        />
      )}
    </SafeAreaView>
  );
}
