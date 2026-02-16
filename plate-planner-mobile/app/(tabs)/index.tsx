import { ScrollView, RefreshControl, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Box, Text, VStack, HStack, Avatar, AvatarFallbackText, Icon, SearchIcon, BellIcon } from "@gluestack-ui/themed";
import { NutritionArc } from "../../src/components/NutritionArc";
import { DietGraph } from "../../src/components/DietGraph";
import { useAuth } from "../../src/state/auth";
import { useState, useCallback, useEffect } from "react";
import { apiRequest } from "../../src/api/client";
import { useFocusEffect } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";

// Partial types for API responses
type NutritionSummary = {
  daily_averages: {
    calories: number;
    protein_g: number;
    carbs_g: number;
    fat_g: number;
  };
  goal_progress: {
    calorie_target: number;
  };
};

type GoalProgressResponse = {
  targets: {
    calories: number;
    protein_g: number;
    carbs_g: number;
    fat_g: number;
  };
};

export default function HomeScreen() {
  const { user } = useAuth();
  const insets = useSafeAreaInsets();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Default values (0) to avoid placeholders
  const [nutrition, setNutrition] = useState({
    calories: 0,
    protein: 0,
    carbs: 0,
    fats: 0,
  });

  const [targets, setTargets] = useState({
    calories: 2000, // Default baseline
    protein: 150,
    carbs: 250,
    fats: 70,
  });

  const fetchData = async () => {
    try {
      // Get today's date in YYYY-MM-DD (local time)
      const now = new Date();
      const year = now.getFullYear();
      const month = String(now.getMonth() + 1).padStart(2, '0');
      const day = String(now.getDate()).padStart(2, '0');
      const todayStr = `${year}-${month}-${day}`;

      // Fetch summary (actuals)
      const summaryPromise = apiRequest<NutritionSummary>(`/nutrition/summary?start_date=${todayStr}&end_date=${todayStr}`)
        .catch(() => null);

      // Fetch goals (targets)
      const goalsPromise = apiRequest<GoalProgressResponse>(`/nutrition/goals/progress`)
        .catch(() => null);

      const [summaryRes, goalsRes] = await Promise.all([summaryPromise, goalsPromise]);

      if (summaryRes?.daily_averages) {
        setNutrition({
          calories: summaryRes.daily_averages.calories || 0,
          protein: summaryRes.daily_averages.protein_g || 0,
          carbs: summaryRes.daily_averages.carbs_g || 0,
          fats: summaryRes.daily_averages.fat_g || 0,
        });
      }

      if (goalsRes?.targets) {
        setTargets({
          calories: goalsRes.targets.calories || 2000,
          protein: goalsRes.targets.protein_g || 150,
          carbs: goalsRes.targets.carbs_g || 250,
          fats: goalsRes.targets.fat_g || 70,
        });
      }
    } catch (err) {
      console.log("Error fetching nutrition data:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      fetchData();
    }, [])
  );

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchData();
  }, []);

  const initials = user?.full_name
    ? user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : "U";

  return (
    <View style={{ flex: 1, backgroundColor: '#FAFAFA' }}>
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{ paddingBottom: 100 }}
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {/* Header with Gradient Background */}
        <Box borderBottomLeftRadius={40} borderBottomRightRadius={40} overflow="hidden" shadowColor="#000" shadowOpacity={0.05} shadowRadius={20} elevation={5} backgroundColor="white">
          <LinearGradient
            colors={['#DCFCE7', '#FFFFFF']} // Premium Light Green Gradient
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={{ paddingTop: insets.top + 20, paddingBottom: 30, paddingHorizontal: 24 }}
          >
            <HStack justifyContent="space-between" alignItems="center">
              <HStack alignItems="center" space="md">
                <Box shadowColor="#16a34a" shadowOffset={{ width: 0, height: 4 }} shadowOpacity={0.3} shadowRadius={8} elevation={5} borderRadius="$full">
                  <Avatar bgColor="$green600" size="md" borderRadius="$full" borderWidth={2} borderColor="white">
                    <AvatarFallbackText>{initials}</AvatarFallbackText>
                  </Avatar>
                </Box>
                <VStack>
                  <Text color="$coolGray500" size="xs" fontWeight="$medium" letterSpacing={0.5} textTransform="uppercase">Welcome Back</Text>
                  <Text color="$coolGray900" bold size="xl">{user?.full_name || "Guest"}</Text>
                </VStack>
              </HStack>
              <HStack space="md">
                <Box w="$10" h="$10" bg="$white" borderRadius="$full" alignItems="center" justifyContent="center" shadowColor="#000" shadowOpacity={0.05} shadowRadius={10} elevation={2}>
                  <Icon as={SearchIcon} color="$coolGray400" />
                </Box>
                <Box w="$10" h="$10" bg="$white" borderRadius="$full" alignItems="center" justifyContent="center" shadowColor="#000" shadowOpacity={0.05} shadowRadius={10} elevation={2}>
                  <Icon as={BellIcon} color="$coolGray400" />
                  <Box position="absolute" top={10} right={10} w="$2" h="$2" bg="$red500" borderRadius="$full" borderWidth={2} borderColor="white" />
                </Box>
              </HStack>
            </HStack>
          </LinearGradient>
        </Box>

        {/* Main Nutrition Card - Overlapping effect */}
        <Box style={{ marginTop: -25 }} mx="$6">
          <Box p="$6" bg="$white" borderRadius="$3xl" shadowColor="#000" shadowOffset={{ width: 0, height: 10 }} shadowOpacity={0.08} shadowRadius={20} elevation={10} borderColor="$coolGray50" borderWidth={1}>
            {/* Header inside card */}
            <HStack justifyContent="space-between" alignItems="center" mb="$2">
              <Text bold size="lg" color="$coolGray800">Today's Goal</Text>
              <Box px="$3" py="$1" bg="$green50" borderRadius="$full">
                <Text size="xs" color="$green700" bold>Daily</Text>
              </Box>
            </HStack>

            <NutritionArc calories={nutrition.calories} target={targets.calories} />

            {/* Macro Row */}
            <HStack justifyContent="space-between" w="$full" mt="$8" px="$2">
              <VStack alignItems="center" flex={1}>
                <Text color="$coolGray400" size="xs" mb={2}>Protein</Text>
                <Text color="$coolGray900" bold size="md">{Math.round(nutrition.protein)}<Text color="$coolGray400" size="sm">/{Math.round(targets.protein)}g</Text></Text>
                <Box h={4} w="100%" bg="$coolGray100" borderRadius="$full" mt={1} overflow="hidden">
                  <Box h="100%" w={`${Math.min((nutrition.protein / targets.protein) * 100, 100)}%`} bg="$green500" borderRadius="$full" />
                </Box>
              </VStack>
              <Box w={16} />
              <VStack alignItems="center" flex={1}>
                <Text color="$coolGray400" size="xs" mb={2}>Fats</Text>
                <Text color="$coolGray900" bold size="md">{Math.round(nutrition.fats)}<Text color="$coolGray400" size="sm">/{Math.round(targets.fats)}g</Text></Text>
                <Box h={4} w="100%" bg="$coolGray100" borderRadius="$full" mt={1} overflow="hidden">
                  <Box h="100%" w={`${Math.min((nutrition.fats / targets.fats) * 100, 100)}%`} bg="$green500" borderRadius="$full" />
                </Box>
              </VStack>
              <Box w={16} />
              <VStack alignItems="center" flex={1}>
                <Text color="$coolGray400" size="xs" mb={2}>Carbs</Text>
                <Text color="$coolGray900" bold size="md">{Math.round(nutrition.carbs)}<Text color="$coolGray400" size="sm">/{Math.round(targets.carbs)}g</Text></Text>
                <Box h={4} w="100%" bg="$coolGray100" borderRadius="$full" mt={1} overflow="hidden">
                  <Box h="100%" w={`${Math.min((nutrition.carbs / targets.carbs) * 100, 100)}%`} bg="$green400" borderRadius="$full" />
                </Box>
              </VStack>
            </HStack>
          </Box>
        </Box>

        {/* Diet Graph Section */}
        <Box mx="$6" mt="$6">
          <HStack alignItems="center" justifyContent="space-between" mb="$4">
            <VStack>
              <Text size="xl" bold color="$coolGray900">Weekly Progress</Text>
              <Text color="$coolGray400" size="sm">See your activity</Text>
            </VStack>
            <Box bg="$green600" px="$3" py="$1.5" borderRadius="$full" shadowColor="#16a34a" shadowOpacity={0.3} shadowRadius={8} elevation={3}>
              <Text color="white" bold size="xs">View All</Text>
            </Box>
          </HStack>

          <Box bg="$white" borderRadius="$3xl" p="$0" overflow="hidden" shadowColor="#000" shadowOffset={{ width: 0, height: 4 }} shadowOpacity={0.06} shadowRadius={12} elevation={4} borderWidth={1} borderColor="$coolGray50">
            {/* Graph Container */}
            <Box p="$4" pb="$0">
              <HStack justifyContent="space-between" alignItems="center" mb="$2">
                <Text color="$coolGray500" size="sm" fontWeight="$medium">Calories Consumed</Text>
                <HStack space="xs" alignItems="baseline">
                  <Text color="$coolGray900" bold size="2xl">{nutrition.calories}</Text>
                  <Text color="$coolGray400" size="xs">kcal</Text>
                </HStack>
              </HStack>
            </Box>

            <Box alignItems="center" justifyContent="flex-end" h={180}>
              <DietGraph />
            </Box>

            {/* Days Row */}
            <Box bg="$coolGray50" p="$4">
              <HStack justifyContent="space-between" w="$full">
                {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day, i) => {
                  const isToday = i === new Date().getDay();
                  return (
                    <VStack key={i} alignItems="center" space="xs">
                      <Text color={isToday ? '$green700' : '$coolGray400'} bold={isToday} size="xs" textTransform="uppercase" fontSize={10}>{day}</Text>
                      <Box w="$2" h="$2" borderRadius="$full" bg={isToday ? '$green500' : '$coolGray300'} opacity={isToday ? 1 : 0.3} />
                    </VStack>
                  );
                })}
              </HStack>
            </Box>
          </Box>
        </Box>

      </ScrollView>
    </View>
  );
}
