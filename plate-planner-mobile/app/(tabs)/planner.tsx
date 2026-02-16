import { ScrollView, TouchableOpacity } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Box, Text, VStack, HStack, Button, ButtonText, Icon, CalendarDaysIcon, Heading, AddIcon, Modal, ModalBackdrop, ModalContent, ModalHeader, ModalCloseButton, ModalBody, ModalFooter, Input, InputField, CloseIcon } from "@gluestack-ui/themed";
import { useState } from "react";

const dates = [
  { day: "Mon", date: "12" },
  { day: "Tue", date: "13", active: true },
  { day: "Wed", date: "14" },
  { day: "Thu", date: "15" },
  { day: "Fri", date: "16" },
];

const initialMeals = [
  { id: "1", meal_type: "Breakfast", time: "8:00 AM", recipe_title: "Avocado Toast with Eggs", calories: 420 },
  { id: "2", meal_type: "Lunch", time: "12:30 PM", recipe_title: "Grilled Chicken Salad", calories: 550 },
  { id: "3", meal_type: "Snack", time: "3:00 PM", recipe_title: "Greek Yogurt & Berries", calories: 180 },
  { id: "4", meal_type: "Dinner", time: "7:00 PM", recipe_title: "Salmon with Quinoa", calories: 620 },
];

export default function PlannerScreen() {
  const [selectedDay, setSelectedDay] = useState("Tue");
  const [meals, setMeals] = useState(initialMeals);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newMealName, setNewMealName] = useState("");
  const [newMealCals, setNewMealCals] = useState("");
  const [newMealType, setNewMealType] = useState("Snack");

  const handleAddMeal = () => {
    if (!newMealName || !newMealCals) return;
    const newMeal = {
      id: Date.now().toString(),
      meal_type: newMealType,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      recipe_title: newMealName,
      calories: parseInt(newMealCals) || 0
    };
    setMeals([...meals, newMeal]);
    setShowAddModal(false);
    setNewMealName("");
    setNewMealCals("");
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#FAFAFA' }} edges={["top", "left", "right"]}>
      <Box px="$6" py="$4">
        <HStack justifyContent="space-between" alignItems="center">
          <VStack>
            <Text size="sm" color="$coolGray400">This Week</Text>
            <Heading size="xl" color="$coolGray900">Meal Plan</Heading>
          </VStack>
          <HStack space="md">
            <TouchableOpacity onPress={() => setShowAddModal(true)}>
              <Box w="$10" h="$10" bg="$green600" borderRadius="$full" alignItems="center" justifyContent="center" shadowColor="#16a34a" shadowOffset={{ width: 0, height: 4 }} shadowOpacity={0.3} shadowRadius={8}>
                <Icon as={AddIcon} size="lg" color="white" />
              </Box>
            </TouchableOpacity>
          </HStack>
        </HStack>
      </Box>

      {/* Date Strip */}
      <HStack px="$6" mb="$6" space="sm">
        {dates.map((d) => (
          <Box
            key={d.day}
            flex={1}
            py="$3"
            borderRadius="$xl"
            bg={d.day === selectedDay ? "$green600" : "$white"}
            borderWidth={1}
            borderColor={d.day === selectedDay ? "$green600" : "$coolGray100"}
            alignItems="center"
          >
            <Text color={d.day === selectedDay ? "$white" : "$coolGray400"} size="xs">{d.day}</Text>
            <Text color={d.day === selectedDay ? "$white" : "$coolGray900"} bold size="lg">{d.date}</Text>
          </Box>
        ))}
      </HStack>

      <ScrollView contentContainerStyle={{ paddingHorizontal: 24, paddingBottom: 100 }}>
        <Text size="sm" color="$coolGray500" bold mb="$4" textTransform="uppercase">Today's Meals</Text>

        {meals.map((meal, index) => (
          <HStack key={meal.id} mb="$4" bg="$white" p="$4" borderRadius="$2xl" borderWidth={1} borderColor="$coolGray100" alignItems="center" space="md">
            <Box w="$12" h="$12" borderRadius="$xl" bg={
              meal.meal_type === "Breakfast" ? "$yellow100" :
                meal.meal_type === "Lunch" ? "$green100" :
                  meal.meal_type === "Snack" ? "$blue100" : "$orange100"
            } alignItems="center" justifyContent="center">
              <Text size="lg">{
                meal.meal_type === "Breakfast" ? "🌅" :
                  meal.meal_type === "Lunch" ? "🥗" :
                    meal.meal_type === "Snack" ? "🍎" : "🍽️"
              }</Text>
            </Box>
            <VStack flex={1}>
              <HStack justifyContent="space-between">
                <Text bold color="$coolGray900" size="md">{meal.recipe_title}</Text>
              </HStack>
              <HStack space="md" mt="$1">
                <Text size="xs" color="$orange500" bold>{meal.meal_type}</Text>
                <Text size="xs" color="$coolGray400">{meal.time}</Text>
                <Text size="xs" color="$coolGray400">{meal.calories} kcal</Text>
              </HStack>
            </VStack>
          </HStack>
        ))}

        {/* Daily Summary */}
        <Box bg="$green600" p="$5" borderRadius="$2xl" mt="$2">
          <HStack justifyContent="space-between" alignItems="center">
            <VStack>
              <Text color="$white" bold size="lg">Daily Total</Text>
              <Text color="$green100" size="sm">{meals.length} meals planned</Text>
            </VStack>
            <VStack alignItems="flex-end">
              <Text color="$white" bold size="2xl">{meals.reduce((sum, m) => sum + m.calories, 0).toLocaleString()}</Text>
              <Text color="$green100" size="sm">of 2,213 kcal</Text>
            </VStack>
          </HStack>
        </Box>
      </ScrollView>

      {/* Add Meal Modal */}
      <Modal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        finalFocusRef={undefined}
      >
        <ModalBackdrop />
        <ModalContent p="$6" borderRadius="$2xl" bg="white">
          <ModalHeader>
            <Heading size="lg">Log Meal</Heading>
            <ModalCloseButton>
              <Icon as={CloseIcon} />
            </ModalCloseButton>
          </ModalHeader>
          <ModalBody py="$4">
            <VStack space="md">
              <Box>
                <Text size="sm" mb="$1" color="$coolGray500">Meal Name</Text>
                <Input variant="outline" size="md" borderRadius="$lg" borderColor="$coolGray200">
                  <InputField placeholder="e.g. Oatmeal" value={newMealName} onChangeText={setNewMealName} autoFocus />
                </Input>
              </Box>
              <Box>
                <Text size="sm" mb="$1" color="$coolGray500">Calories (kcal)</Text>
                <Input variant="outline" size="md" borderRadius="$lg" borderColor="$coolGray200">
                  <InputField placeholder="e.g. 350" keyboardType="numeric" value={newMealCals} onChangeText={setNewMealCals} />
                </Input>
              </Box>
              <Box>
                <Text size="sm" mb="$1" color="$coolGray500">Type</Text>
                <HStack space="sm">
                  {["Breakfast", "Lunch", "Dinner", "Snack"].map(t => (
                    <TouchableOpacity key={t} onPress={() => setNewMealType(t)} style={{ flex: 1 }}>
                      <Box
                        bg={newMealType === t ? "$green600" : "$coolGray100"}
                        py="$2"
                        borderRadius="$lg"
                        alignItems="center"
                      >
                        <Text size="xs" color={newMealType === t ? "white" : "$coolGray600"} bold>{t}</Text>
                      </Box>
                    </TouchableOpacity>
                  ))}
                </HStack>
              </Box>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button
              variant="outline"
              action="secondary"
              mr="$3"
              onPress={() => setShowAddModal(false)}
              borderColor="$coolGray200"
              borderRadius="$xl"
            >
              <ButtonText color="$coolGray600">Cancel</ButtonText>
            </Button>
            <Button
              size="md"
              bg="$green600"
              borderRadius="$xl"
              onPress={handleAddMeal}
            >
              <ButtonText color="white" bold>Add Meal</ButtonText>
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </SafeAreaView >
  );
}
