import {
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import {
  Box,
  Text,
  VStack,
  HStack,
  Button,
  ButtonText,
} from "@gluestack-ui/themed";
import { useState, useEffect } from "react";
import { useRouter } from "expo-router";
import { useAuth } from "../src/state/auth";
import { apiRequest } from "../src/api/client";

type GoalType = "weight_loss" | "muscle_gain" | "maintenance" | "general_health";

const GOAL_OPTIONS: { key: GoalType; label: string; icon: string; desc: string; defaultCals: number }[] = [
  { key: "weight_loss", label: "Weight Loss", icon: "🔥", desc: "Calorie deficit to lose weight", defaultCals: 1600 },
  { key: "muscle_gain", label: "Muscle Gain", icon: "💪", desc: "Calorie surplus to build muscle", defaultCals: 2500 },
  { key: "maintenance", label: "Maintenance", icon: "⚖️", desc: "Maintain current body weight", defaultCals: 2000 },
  { key: "general_health", label: "General Health", icon: "🥗", desc: "Balanced nutrition for wellness", defaultCals: 2000 },
];

const DURATION_OPTIONS = [
  { label: "30 days", days: 30 },
  { label: "60 days", days: 60 },
  { label: "90 days", days: 90 },
  { label: "Ongoing", days: null },
];

export default function NutritionGoalsScreen() {
  const router = useRouter();
  const { token } = useAuth();

  const [goalType, setGoalType] = useState<GoalType>("maintenance");
  const [calorieTarget, setCalorieTarget] = useState("2000");
  const [proteinTarget, setProteinTarget] = useState("150");
  const [carbsTarget, setCarbsTarget] = useState("200");
  const [fatTarget, setFatTarget] = useState("65");
  const [durationDays, setDurationDays] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [currentGoal, setCurrentGoal] = useState<any>(null);
  const [loadingCurrent, setLoadingCurrent] = useState(true);

  // Load existing active goal
  useEffect(() => {
    if (!token) return;
    apiRequest<any>("/nutrition/goals/progress", { token })
      .then(data => {
        if (data?.active_goal) {
          setCurrentGoal(data.active_goal);
          if (data.active_goal.goal_type) setGoalType(data.active_goal.goal_type);
          if (data.targets?.calories) setCalorieTarget(String(data.targets.calories));
          if (data.targets?.protein_g) setProteinTarget(String(data.targets.protein_g));
          if (data.targets?.carbs_g) setCarbsTarget(String(data.targets.carbs_g));
          if (data.targets?.fat_g) setFatTarget(String(data.targets.fat_g));
        }
      })
      .catch(() => {})
      .finally(() => setLoadingCurrent(false));
  }, [token]);

  // Auto-fill calories when goal type changes
  const handleGoalTypeChange = (key: GoalType) => {
    setGoalType(key);
    const opt = GOAL_OPTIONS.find(o => o.key === key);
    if (opt) setCalorieTarget(String(opt.defaultCals));
  };

  const handleSave = async () => {
    const cals = parseInt(calorieTarget);
    if (!cals || cals < 800 || cals > 10000) {
      Alert.alert("Invalid Calories", "Please enter a calorie target between 800 and 10,000.");
      return;
    }
    if (!token) return;
    setSaving(true);
    try {
      const today = new Date().toISOString().split("T")[0];
      await apiRequest("/nutrition/goals", {
        method: "POST",
        token,
        body: {
          goal_type: goalType,
          daily_calorie_target: cals,
          daily_protein_g_target: parseInt(proteinTarget) || null,
          daily_carbs_g_target: parseInt(carbsTarget) || null,
          daily_fat_g_target: parseInt(fatTarget) || null,
          start_date: today,
          duration_days: durationDays,
        },
      });
      Alert.alert("Goal Saved! 🎯", "Your nutrition goal has been set. Track your progress in the Meal Log.", [
        { text: "OK", onPress: () => router.back() },
      ]);
    } catch (e: any) {
      Alert.alert("Error", e?.message || "Failed to save goal.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#FAFAFA" }} edges={["top", "left", "right"]}>
      {/* Header */}
      <Box px="$6" pt="$4" pb="$4" bg="$white" shadowColor="$black" shadowOffset={{ width: 0, height: 2 }} shadowOpacity={0.04} shadowRadius={4} elevation={2}>
        <HStack alignItems="center" justifyContent="space-between">
          <TouchableOpacity onPress={() => router.back()} accessibilityLabel="Go back" accessibilityRole="button">
            <Text color="$green600" bold>‹ Back</Text>
          </TouchableOpacity>
          <Text size="xl" bold color="$coolGray900">Nutrition Goals</Text>
          <Box w={50} />
        </HStack>
      </Box>

      <ScrollView contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 120 }}>

        {/* Current Goal Banner */}
        {!loadingCurrent && currentGoal && (
          <Box mt="$4" mb="$2" p="$4" bg="$green50" borderRadius="$xl" borderWidth={1} borderColor="$green200">
            <HStack space="sm" alignItems="center">
              <Text size="lg">✅</Text>
              <VStack>
                <Text bold color="$green800" size="sm">Active Goal</Text>
                <Text color="$green700" size="xs">
                  {GOAL_OPTIONS.find(o => o.key === currentGoal.goal_type)?.label || currentGoal.goal_type} · Started {currentGoal.start_date}
                </Text>
              </VStack>
            </HStack>
          </Box>
        )}

        {/* Goal Type */}
        <Text bold color="$coolGray800" size="md" mt="$5" mb="$3">What's your goal?</Text>
        <VStack space="sm" mb="$6">
          {GOAL_OPTIONS.map(opt => (
            <TouchableOpacity key={opt.key} onPress={() => handleGoalTypeChange(opt.key)} activeOpacity={0.8}>
              <Box
                bg="$white"
                borderRadius="$xl"
                p="$4"
                borderWidth={2}
                borderColor={goalType === opt.key ? "$green500" : "$coolGray100"}
              >
                <HStack alignItems="center" space="md">
                  <Box
                    w={44} h={44}
                    bg={goalType === opt.key ? "$green100" : "$coolGray50"}
                    borderRadius="$full"
                    alignItems="center"
                    justifyContent="center"
                  >
                    <Text size="xl">{opt.icon}</Text>
                  </Box>
                  <VStack flex={1}>
                    <Text bold color={goalType === opt.key ? "$green700" : "$coolGray800"}>{opt.label}</Text>
                    <Text size="xs" color="$coolGray500">{opt.desc}</Text>
                  </VStack>
                  {goalType === opt.key && (
                    <Box w={22} h={22} bg="$green500" borderRadius="$full" alignItems="center" justifyContent="center">
                      <Text color="$white" size="xs">✓</Text>
                    </Box>
                  )}
                </HStack>
              </Box>
            </TouchableOpacity>
          ))}
        </VStack>

        {/* Calorie Target */}
        <Text bold color="$coolGray800" size="md" mb="$3">Daily Calorie Target</Text>
        <Box bg="$white" borderRadius="$xl" p="$4" mb="$6" borderWidth={1} borderColor="$coolGray100">
          <HStack alignItems="center" space="md">
            <TextInput
              value={calorieTarget}
              onChangeText={setCalorieTarget}
              keyboardType="numeric"
              style={{ fontSize: 32, fontWeight: "bold", color: "#16a34a", flex: 1 }}
            />
            <Text color="$coolGray500" size="lg">kcal / day</Text>
          </HStack>
          <Text size="xs" color="$coolGray400" mt="$1">Typical range: 1,200–4,000 kcal</Text>
        </Box>

        {/* Macro Targets */}
        <Text bold color="$coolGray800" size="md" mb="$3">Macro Targets (optional)</Text>
        <Box bg="$white" borderRadius="$xl" p="$4" mb="$6" borderWidth={1} borderColor="$coolGray100">
          <VStack space="md">
            {[
              { label: "🥩 Protein", value: proteinTarget, setter: setProteinTarget, color: "#3b82f6" },
              { label: "🌾 Carbs", value: carbsTarget, setter: setCarbsTarget, color: "#f59e0b" },
              { label: "🥑 Fat", value: fatTarget, setter: setFatTarget, color: "#ef4444" },
            ].map(({ label, value, setter, color }) => (
              <HStack key={label} alignItems="center" justifyContent="space-between">
                <Text color="$coolGray700" bold size="sm">{label}</Text>
                <HStack alignItems="center" space="sm">
                  <TextInput
                    value={value}
                    onChangeText={setter}
                    keyboardType="numeric"
                    style={{ fontSize: 18, fontWeight: "bold", color, width: 60, textAlign: "right" }}
                  />
                  <Text color="$coolGray400" size="sm">g/day</Text>
                </HStack>
              </HStack>
            ))}
          </VStack>
        </Box>

        {/* Duration */}
        <Text bold color="$coolGray800" size="md" mb="$3">Duration</Text>
        <HStack space="sm" flexWrap="wrap" mb="$8">
          {DURATION_OPTIONS.map(opt => (
            <TouchableOpacity key={opt.label} onPress={() => setDurationDays(opt.days)} activeOpacity={0.8}>
              <Box
                px="$4" py="$2"
                borderRadius="$full"
                borderWidth={1.5}
                bg={durationDays === opt.days ? "$green600" : "$white"}
                borderColor={durationDays === opt.days ? "$green600" : "$coolGray200"}
                mb="$2"
              >
                <Text
                  size="sm"
                  bold={durationDays === opt.days}
                  color={durationDays === opt.days ? "$white" : "$coolGray600"}
                >
                  {opt.label}
                </Text>
              </Box>
            </TouchableOpacity>
          ))}
        </HStack>

      </ScrollView>

      {/* Save Button */}
      <Box position="absolute" bottom={30} left={20} right={20}>
        <Button
          bg="$green600"
          borderRadius="$xl"
          h={56}
          onPress={handleSave}
          disabled={saving}
          shadowColor="$green600"
          shadowOffset={{ width: 0, height: 4 }}
          shadowOpacity={0.3}
          shadowRadius={8}
        >
          {saving ? (
            <ActivityIndicator size="small" color="white" />
          ) : (
            <ButtonText color="$white" bold size="md">Save Goal 🎯</ButtonText>
          )}
        </Button>
      </Box>
    </SafeAreaView>
  );
}
