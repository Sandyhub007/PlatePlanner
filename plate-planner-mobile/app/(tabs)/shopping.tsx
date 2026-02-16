import { ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Box, Text, VStack, HStack, Button, ButtonText, Icon, CircleIcon, CheckCircleIcon, Heading } from "@gluestack-ui/themed";
import { useState } from "react";

const mockShoppingList = {
  "Produce": [
    { id: "1", name: "Avocados", quantity: "3", unit: "pcs", checked: false },
    { id: "2", name: "Baby Spinach", quantity: "200", unit: "g", checked: true },
    { id: "3", name: "Cherry Tomatoes", quantity: "1", unit: "pack", checked: false },
    { id: "4", name: "Fresh Berries", quantity: "250", unit: "g", checked: false },
  ],
  "Protein": [
    { id: "5", name: "Chicken Breast", quantity: "500", unit: "g", checked: true },
    { id: "6", name: "Salmon Fillet", quantity: "2", unit: "pcs", checked: false },
    { id: "7", name: "Eggs (Free Range)", quantity: "12", unit: "pcs", checked: true },
  ],
  "Dairy & Grains": [
    { id: "8", name: "Greek Yogurt", quantity: "500", unit: "ml", checked: false },
    { id: "9", name: "Quinoa", quantity: "300", unit: "g", checked: false },
    { id: "10", name: "Sourdough Bread", quantity: "1", unit: "loaf", checked: true },
  ],
};

export default function ShoppingScreen() {
  const [items, setItems] = useState(mockShoppingList);

  const toggleItem = (category: string, id: string) => {
    setItems(prev => ({
      ...prev,
      [category]: prev[category as keyof typeof prev].map(item =>
        item.id === id ? { ...item, checked: !item.checked } : item
      ),
    }));
  };

  const totalItems = Object.values(items).flat().length;
  const checkedItems = Object.values(items).flat().filter(i => i.checked).length;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#FAFAFA' }} edges={["top", "left", "right"]}>
      <Box px="$6" py="$4">
        <HStack justifyContent="space-between" alignItems="center">
          <VStack>
            <Text size="sm" color="$coolGray400">This Week</Text>
            <Heading size="xl" color="$coolGray900">Shopping List</Heading>
          </VStack>
          <Box px="$3" py="$1" bg="$green100" borderRadius="$full">
            <Text color="$green700" size="sm" bold>{checkedItems}/{totalItems} done</Text>
          </Box>
        </HStack>
      </Box>

      <ScrollView contentContainerStyle={{ paddingHorizontal: 24, paddingBottom: 120 }}>
        {Object.entries(items).map(([category, categoryItems]) => (
          <Box key={category} mb="$6">
            <Text size="xs" color="$green600" bold mb="$3" textTransform="uppercase" letterSpacing="$lg">{category}</Text>
            <Box bg="$white" borderRadius="$2xl" borderWidth={1} borderColor="$coolGray100" overflow="hidden">
              {categoryItems.map((item, index) => (
                <HStack
                  key={item.id}
                  p="$4"
                  alignItems="center"
                  borderBottomWidth={index === categoryItems.length - 1 ? 0 : 1}
                  borderColor="$coolGray50"
                  onTouchEnd={() => toggleItem(category, item.id)}
                  opacity={item.checked ? 0.5 : 1}
                >
                  <Box w="$6" h="$6" borderRadius="$full" borderWidth={2} borderColor={item.checked ? "$green500" : "$coolGray300"} bg={item.checked ? "$green500" : "transparent"} alignItems="center" justifyContent="center" mr="$3">
                    {item.checked && <Text color="$white" size="xs" bold>✓</Text>}
                  </Box>
                  <VStack flex={1}>
                    <Text color="$coolGray900" size="md" strikeThrough={item.checked}>{item.name}</Text>
                    <Text color="$coolGray400" size="sm">{item.quantity} {item.unit}</Text>
                  </VStack>
                </HStack>
              ))}
            </Box>
          </Box>
        ))}
      </ScrollView>

      <Box position="absolute" bottom={24} left={24} right={24}>
        <Button size="lg" bg="$green600" borderRadius="$full" shadowColor="$black" shadowOffset={{ width: 0, height: 4 }} shadowOpacity={0.15} shadowRadius={8}>
          <ButtonText color="$white" bold>+ Add Item</ButtonText>
        </Button>
      </Box>
    </SafeAreaView>
  );
}
