import { ScrollView, TouchableOpacity, ImageBackground } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Box, Text, VStack, HStack, Icon, ChevronLeftIcon, ChevronRightIcon, AddIcon, Divider, Button, ButtonText, CalendarDaysIcon } from "@gluestack-ui/themed";
import { useState } from "react";
import { LinearGradient } from "expo-linear-gradient";
import * as ImagePicker from 'expo-image-picker';
import { useAuth } from "../../src/state/auth";
import { apiUploadRequest } from "../../src/api/client";

// Generate this week's dates
const generateWeek = () => {
  const dates = [];
  const curr = new Date();
  const first = curr.getDate() - curr.getDay(); // First day is Sunday

  for (let i = 0; i < 7; i++) {
    const day = new Date(curr.setDate(first + i));
    dates.push({
      date: day.getDate(),
      day: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][day.getDay()],
      fullDate: day.toISOString().split('T')[0],
      isToday: day.getDate() === new Date().getDate() && day.getMonth() === new Date().getMonth(),
    });
  }
  return dates;
};

export default function MealPlannerScreen() {
  const { token } = useAuth();
  const [weekDates] = useState(generateWeek());
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0]);

  // Meal Data State
  const [meals, setMeals] = useState<Record<string, { type: string, filled: boolean, title?: string, image?: string, calories?: number }>>({
    Breakfast: { type: 'Breakfast', filled: true, title: 'Avocado Toast & Egg', image: 'https://images.unsplash.com/photo-1525351484163-7529414344d8?w=800&q=80', calories: 420 },
    Lunch: { type: 'Lunch', filled: false },
    Dinner: { type: 'Dinner', filled: true, title: 'Lemon Herb Grilled Salmon', image: 'https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=800&q=80', calories: 580 },
    Snacks: { type: 'Snacks', filled: false },
  });

  const handlePickImage = async (mealKey: string) => {
    let result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      aspect: [16, 9],
      quality: 0.8,
    });

    if (!result.canceled && result.assets && result.assets.length > 0) {
      const asset = result.assets[0];

      // Optioanlly set loading state here...

      const formData = new FormData();
      // React Native FormData requires { uri, name, type }
      const uriParts = asset.uri.split('.');
      const fileType = uriParts[uriParts.length - 1];

      formData.append('file', {
        uri: asset.uri,
        name: `photo.${fileType}`,
        type: `image/${fileType}`,
      } as any);

      formData.append('meal_type', meals[mealKey].type);
      formData.append('meal_date', selectedDate);
      formData.append('title', 'My Custom Meal');

      try {
        const response = await apiUploadRequest<{ image_url: string }>(
          "/user-meals/upload",
          formData,
          token
        );

        // Update local state with the permanent URL
        setMeals(prev => ({
          ...prev,
          [mealKey]: {
            ...prev[mealKey],
            filled: true,
            title: 'My Custom Meal',
            image: response.image_url, // Permanent Vercel URL
          }
        }));
      } catch (err) {
        console.error("Failed to upload image", err);
        alert("Failed to save meal photo. Please try again.");
      }
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#FAFAFA' }} edges={["top", "left", "right"]}>
      <ScrollView contentContainerStyle={{ paddingBottom: 100 }} showsVerticalScrollIndicator={false}>

        {/* Header */}
        <Box px="$6" pt="$4" pb="$4" bg="$white" shadowColor="$black" shadowOffset={{ width: 0, height: 4 }} shadowOpacity={0.03} shadowRadius={8} elevation={2} zIndex={10}>
          <HStack alignItems="center" justifyContent="space-between" mb="$6">
            <VStack>
              <Text color="$coolGray500" size="sm" bold textTransform="uppercase" letterSpacing={1}>This Week</Text>
              <Text size="3xl" bold color="$coolGray900">Meal Plan</Text>
            </VStack>
            <Box p="$2" bg="$green50" borderRadius="$full">
              <Icon as={CalendarDaysIcon} color="$green600" size="xl" />
            </Box>
          </HStack>

          {/* Date Selector */}
          <HStack justifyContent="space-between">
            {weekDates.map((d, i) => {
              const isSelected = d.fullDate === selectedDate;
              return (
                <TouchableOpacity key={i} onPress={() => setSelectedDate(d.fullDate)} activeOpacity={0.7}>
                  <VStack
                    alignItems="center"
                    p="$2"
                    w={44}
                    h={65}
                    borderRadius="$full"
                    bg={isSelected ? "$green600" : d.isToday ? "$green50" : "transparent"}
                    shadowColor={isSelected ? "$green600" : "transparent"}
                    shadowOffset={{ width: 0, height: 4 }}
                    shadowOpacity={0.3}
                    shadowRadius={6}
                    elevation={isSelected ? 4 : 0}
                  >
                    <Text color={isSelected ? "$white" : d.isToday ? "$green700" : "$coolGray400"} size="xs" bold={isSelected} mb="$1">
                      {d.day}
                    </Text>
                    <Text color={isSelected ? "$white" : "$coolGray900"} size="md" bold={isSelected}>
                      {d.date}
                    </Text>
                  </VStack>
                </TouchableOpacity>
              );
            })}
          </HStack>
        </Box>

        {/* Nutritional Summary Banner */}
        <Box px="$6" mt="$6" mb="$6">
          <LinearGradient colors={['#D1FAE5', '#A7F3D0']} style={{ borderRadius: 20, padding: 16 }}>
            <HStack justifyContent="space-between" alignItems="center">
              <VStack>
                <Text color="$green800" bold>Daily Goal Progress</Text>
                <Text color="$green700" size="sm">1,000 / 2,000 kcal planned</Text>
              </VStack>
              <Box w={40} h={40} borderRadius="$full" bg="$white" alignItems="center" justifyContent="center">
                <Text color="$green600" bold>50%</Text>
              </Box>
            </HStack>
          </LinearGradient>
        </Box>

        {/* Meal Slots */}
        <Box px="$6">
          {Object.entries(meals).map(([mealKey, meal]) => (
            <Box key={mealKey} mb="$6">

              <HStack justifyContent="space-between" alignItems="center" mb="$3">
                <Text size="lg" bold color="$coolGray900">{meal.type}</Text>
                {meal.calories && (
                  <Text size="xs" color="$green600" bold bg="$green100" px="$2" py="$0.5" borderRadius="$full">
                    {meal.calories} kcal
                  </Text>
                )}
              </HStack>

              {meal.filled ? (
                /* Filled Meal Card */
                <TouchableOpacity activeOpacity={0.8} onPress={() => handlePickImage(mealKey)}>
                  <Box bg="$white" borderRadius="$2xl" overflow="hidden" shadowColor="$black" shadowOffset={{ width: 0, height: 4 }} shadowOpacity={0.06} shadowRadius={10} elevation={3} borderWidth={1} borderColor="$coolGray50">
                    <ImageBackground source={{ uri: meal.image }} style={{ height: 120, width: '100%' }}>
                      <LinearGradient colors={['rgba(0,0,0,0)', 'rgba(0,0,0,0.8)']} style={{ position: 'absolute', top: 0, bottom: 0, left: 0, right: 0 }} />
                      <Box position="absolute" bottom={0} left={0} p="$4">
                        <Text color="$white" bold size="md">{meal.title}</Text>
                      </Box>
                      <Box position="absolute" top={10} right={10} bg="rgba(0,0,0,0.5)" borderRadius="$full" p="$1">
                        <Icon as={AddIcon} color="white" style={{ transform: [{ rotate: '45deg' }] }} />
                      </Box>
                    </ImageBackground>
                  </Box>
                </TouchableOpacity>
              ) : (
                /* Empty Meal Slot */
                <TouchableOpacity activeOpacity={0.7} onPress={() => handlePickImage(mealKey)}>
                  <Box bg="$white" borderRadius="$2xl" borderStyle="dashed" borderWidth={1.5} borderColor="$coolGray300" h={120} alignItems="center" justifyContent="center">
                    <Box bg="$green50" w={40} h={40} borderRadius="$full" alignItems="center" justifyContent="center" mb="$2">
                      <Icon as={AddIcon} color="$green600" />
                    </Box>
                    <Text color="$coolGray500" bold>Add {meal.type.toLowerCase()}</Text>
                    <Text color="$coolGray400" size="xs">Tap to upload a photo</Text>
                  </Box>
                </TouchableOpacity>
              )}
            </Box>
          ))}
        </Box>

      </ScrollView>
    </SafeAreaView>
  );
}
