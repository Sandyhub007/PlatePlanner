import { ScrollView, TouchableOpacity, TextInput, Animated, PanResponder, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Box, Text, VStack, HStack, Button, ButtonText, Heading } from "@gluestack-ui/themed";
import { useState, useRef, useCallback } from "react";
import * as Haptics from "expo-haptics";
import { useAuth } from "../../src/state/auth";
import { apiRequest } from "../../src/api/client";
import { useFocusEffect } from "expo-router";

type ShoppingItem = {
  id: string;
  ingredient_name: string;
  quantity?: number | null;
  unit?: string | null;
  category: string;
  is_purchased: boolean;
  estimated_price?: number | null;
};

type ShoppingListData = {
  id: string;
  name: string;
  status: string;
  total_items: number;
  purchased_items: number;
  items_by_category: Record<string, ShoppingItem[]>;
};

type ShoppingListSummary = {
  id: string;
  name: string;
  status: string;
  total_items: number;
  purchased_items: number;
};

// ── Swipeable Item ─────────────────────────────────────────────────────────────
function SwipeableItem({
  item,
  onToggle,
  onRemove,
}: {
  item: ShoppingItem;
  onToggle: () => void;
  onRemove: () => void;
}) {
  const translateX = useRef(new Animated.Value(0)).current;
  const SWIPE_THRESHOLD = -70;
  const DELETE_THRESHOLD = -100;
  let hasFiredHaptic = useRef(false);

  const panResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_, g) =>
        Math.abs(g.dx) > 8 && Math.abs(g.dy) < 20,
      onPanResponderMove: (_, g) => {
        const clamped = Math.max(-120, Math.min(0, g.dx));
        translateX.setValue(clamped);
        if (clamped < DELETE_THRESHOLD && !hasFiredHaptic.current) {
          Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
          hasFiredHaptic.current = true;
        } else if (clamped >= DELETE_THRESHOLD) {
          hasFiredHaptic.current = false;
        }
      },
      onPanResponderRelease: (_, g) => {
        if (g.dx < DELETE_THRESHOLD) {
          Animated.timing(translateX, {
            toValue: -400,
            duration: 250,
            useNativeDriver: true,
          }).start(() => onRemove());
        } else {
          Animated.spring(translateX, {
            toValue: 0,
            useNativeDriver: true,
            bounciness: 6,
          }).start();
        }
      },
    })
  ).current;

  return (
    <Box overflow="hidden">
      {/* Red delete background */}
      <Box
        position="absolute"
        right={0}
        top={0}
        bottom={0}
        w={100}
        bg="$red500"
        alignItems="center"
        justifyContent="center"
      >
        <Text color="white" bold>Delete</Text>
      </Box>

      <Animated.View style={{ transform: [{ translateX }] }} {...panResponder.panHandlers}>
        <HStack
          p="$4"
          alignItems="center"
          bg="$white"
          opacity={item.is_purchased ? 0.6 : 1}
        >
          <TouchableOpacity
            onPress={() => {
              Haptics.selectionAsync();
              onToggle();
            }}
            style={{ flexDirection: "row", flex: 1, alignItems: "center" }}
            activeOpacity={0.7}
          >
            <Box
              w="$6"
              h="$6"
              borderRadius="$full"
              borderWidth={2}
              borderColor={item.is_purchased ? "$green500" : "$coolGray300"}
              bg={item.is_purchased ? "$green500" : "transparent"}
              alignItems="center"
              justifyContent="center"
              mr="$3"
            >
              {item.is_purchased && <Text color="$white" size="xs" bold>✓</Text>}
            </Box>
            <VStack flex={1}>
              <Text color="$coolGray900" size="md" strikeThrough={item.is_purchased}>
                {item.ingredient_name}
              </Text>
              <Text color="$coolGray400" size="sm">
                {item.quantity ?? ""} {item.unit ?? ""}
              </Text>
            </VStack>
          </TouchableOpacity>
          <Text color="$coolGray300" size="xs">← swipe</Text>
        </HStack>
      </Animated.View>
    </Box>
  );
}

// ── Main Screen ───────────────────────────────────────────────────────────────
export default function ShoppingScreen() {
  const { token } = useAuth();
  const [loading, setLoading] = useState(false);
  const [listId, setListId] = useState<string | null>(null);
  const [items, setItems] = useState<Record<string, ShoppingItem[]>>({});
  const [isAdding, setIsAdding] = useState(false);
  const [newItemName, setNewItemName] = useState("");
  const [newItemCategory, setNewItemCategory] = useState("Produce");
  const CATEGORIES = ["Produce", "Protein", "Dairy & Grains", "Other"];

  const fetchShoppingList = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      // Get the user's shopping lists and load the most recent active one
      const listsRes = await apiRequest<{
        items: ShoppingListSummary[];
        total: number;
      }>("/shopping-lists/?limit=1&offset=0", { token });

      if (listsRes.items.length > 0) {
        const latestList = listsRes.items[0];
        setListId(latestList.id);
        // Fetch full list with categories
        const fullList = await apiRequest<ShoppingListData>(
          `/shopping-lists/${latestList.id}`,
          { token }
        );
        setItems(fullList.items_by_category || {});
      } else {
        setListId(null);
        setItems({});
      }
    } catch (err) {
      console.log("Failed to load shopping list:", err);
      setItems({});
    } finally {
      setLoading(false);
    }
  }, [token]);

  useFocusEffect(
    useCallback(() => {
      fetchShoppingList();
    }, [fetchShoppingList])
  );

  const toggleItem = async (category: string, id: string) => {
    if (!token || !listId) return;
    const item = items[category]?.find((i) => i.id === id);
    if (!item) return;

    // Optimistic update
    setItems((prev) => ({
      ...prev,
      [category]: prev[category].map((i) =>
        i.id === id ? { ...i, is_purchased: !i.is_purchased } : i
      ),
    }));

    try {
      await apiRequest(`/shopping-lists/${listId}/items/${id}`, {
        token,
        method: "PUT",
        body: { is_purchased: !item.is_purchased },
      });
    } catch (err) {
      // Revert on failure
      setItems((prev) => ({
        ...prev,
        [category]: prev[category].map((i) =>
          i.id === id ? { ...i, is_purchased: item.is_purchased } : i
        ),
      }));
      console.log("Failed to toggle item:", err);
    }
  };

  const removeItem = async (category: string, id: string) => {
    if (!token || !listId) return;
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);

    // Optimistic update
    const prevItems = { ...items };
    setItems((prev) => ({
      ...prev,
      [category]: prev[category].filter((i) => i.id !== id),
    }));

    try {
      await apiRequest(`/shopping-lists/${listId}/items/${id}`, {
        token,
        method: "DELETE",
      });
    } catch (err) {
      setItems(prevItems);
      console.log("Failed to remove item:", err);
    }
  };

  const addItem = async () => {
    if (!newItemName.trim() || !token || !listId) return;
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);

    try {
      const newItem = await apiRequest<ShoppingItem>(
        `/shopping-lists/${listId}/items`,
        {
          token,
          method: "POST",
          body: {
            ingredient_name: newItemName.trim(),
            quantity: 1,
            unit: "pcs",
            category: newItemCategory,
          },
        }
      );
      setItems((prev) => ({
        ...prev,
        [newItemCategory]: [...(prev[newItemCategory] || []), newItem],
      }));
      setNewItemName("");
      setIsAdding(false);
    } catch (err) {
      console.log("Failed to add item:", err);
      alert("Failed to add item. Please try again.");
    }
  };

  const allItems = Object.values(items).flat();
  const totalItems = allItems.length;
  const checkedItems = allItems.filter((i) => i.is_purchased).length;
  const progress = totalItems > 0 ? checkedItems / totalItems : 0;

  // Not authenticated
  if (!token) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: "#FAFAFA" }} edges={["top", "left", "right"]}>
        <Box flex={1} alignItems="center" justifyContent="center" px="$6">
          <Text size="4xl" mb="$4">🔒</Text>
          <Text size="lg" bold color="$coolGray900" mb="$2">Sign in required</Text>
          <Text color="$coolGray500" textAlign="center">
            Sign in to view and manage your shopping lists.
          </Text>
        </Box>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#FAFAFA" }} edges={["top", "left", "right"]}>
      {/* Header */}
      <Box px="$6" py="$4">
        <HStack justifyContent="space-between" alignItems="center" mb="$2">
          <VStack>
            <Text size="sm" color="$coolGray400">This Week</Text>
            <Heading size="xl" color="$coolGray900">Shopping List</Heading>
          </VStack>
          {totalItems > 0 && (
            <Box px="$3" py="$1" bg="$green100" borderRadius="$full">
              <Text color="$green700" size="sm" bold>
                {checkedItems}/{totalItems} done
              </Text>
            </Box>
          )}
        </HStack>

        {/* Progress bar */}
        {totalItems > 0 && (
          <>
            <Box h={6} bg="$coolGray100" borderRadius="$full" overflow="hidden">
              <Box
                h="$full"
                borderRadius="$full"
                style={{ width: `${progress * 100}%`, backgroundColor: "#16a34a" }}
              />
            </Box>
            {progress === 1 && totalItems > 0 && (
              <Text size="xs" color="$green600" bold mt="$1">All done! Great shopping trip!</Text>
            )}
          </>
        )}
      </Box>

      {/* Add item form */}
      {isAdding && listId && (
        <Box px="$6" pb="$4">
          <VStack style={{ gap: 12 }}>
            <HStack alignItems="center" style={{ gap: 8 }}>
              <Box
                flex={1}
                bg="$white"
                borderRadius="$xl"
                borderWidth={1}
                borderColor="$coolGray200"
                px="$4"
                py="$3"
              >
                <TextInput
                  placeholder="Item name (e.g. Milk)"
                  value={newItemName}
                  onChangeText={setNewItemName}
                  style={{ fontSize: 16 }}
                  autoFocus
                  onSubmitEditing={addItem}
                  returnKeyType="done"
                />
              </Box>
              <TouchableOpacity onPress={addItem}>
                <Box bg="$green600" px="$4" py="$3" borderRadius="$xl">
                  <Text color="$white" bold>Add</Text>
                </Box>
              </TouchableOpacity>
              <TouchableOpacity onPress={() => setIsAdding(false)}>
                <Box bg="$coolGray200" px="$4" py="$3" borderRadius="$xl">
                  <Text color="$coolGray700" bold>✕</Text>
                </Box>
              </TouchableOpacity>
            </HStack>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              <HStack style={{ gap: 8 }} py="$1">
                {CATEGORIES.map((cat) => (
                  <TouchableOpacity
                    key={cat}
                    onPress={() => {
                      Haptics.selectionAsync();
                      setNewItemCategory(cat);
                    }}
                  >
                    <Box
                      px="$4"
                      py="$2"
                      borderRadius="$full"
                      borderWidth={1}
                      borderColor={newItemCategory === cat ? "$green600" : "$coolGray300"}
                      bg={newItemCategory === cat ? "$green50" : "transparent"}
                    >
                      <Text
                        size="sm"
                        color={newItemCategory === cat ? "$green700" : "$coolGray600"}
                        bold={newItemCategory === cat}
                      >
                        {cat}
                      </Text>
                    </Box>
                  </TouchableOpacity>
                ))}
              </HStack>
            </ScrollView>
          </VStack>
        </Box>
      )}

      <ScrollView contentContainerStyle={{ paddingHorizontal: 24, paddingBottom: 120 }}>
        {/* Loading */}
        {loading && (
          <Box alignItems="center" py="$10">
            <ActivityIndicator size="large" color="#16a34a" />
            <Text color="$coolGray500" mt="$4">Loading shopping list...</Text>
          </Box>
        )}

        {/* Empty state */}
        {!loading && totalItems === 0 && (
          <Box alignItems="center" py="$10">
            <Text size="4xl" mb="$4">🛒</Text>
            <Text size="lg" bold color="$coolGray900" mb="$2">
              No shopping list yet
            </Text>
            <Text color="$coolGray500" textAlign="center" px="$4">
              Generate a meal plan first, then create a shopping list from it.
            </Text>
          </Box>
        )}

        {/* Items by category */}
        {!loading && totalItems > 0 && (
          <>
            <Text size="xs" color="$coolGray400" mb="$4">
              ← Swipe left on any item to remove it
            </Text>

            {Object.entries(items).map(([category, categoryItems]) => {
              if (categoryItems.length === 0) return null;
              return (
                <Box key={category} mb="$6">
                  <Text
                    size="xs"
                    color="$green600"
                    bold
                    mb="$3"
                    textTransform="uppercase"
                    letterSpacing="$lg"
                  >
                    {category}
                  </Text>
                  <Box
                    bg="$white"
                    borderRadius="$2xl"
                    borderWidth={1}
                    borderColor="$coolGray100"
                    overflow="hidden"
                  >
                    {categoryItems.map((item, index) => (
                      <Box
                        key={item.id}
                        borderBottomWidth={index === categoryItems.length - 1 ? 0 : 1}
                        borderColor="$coolGray50"
                      >
                        <SwipeableItem
                          item={item}
                          onToggle={() => toggleItem(category, item.id)}
                          onRemove={() => removeItem(category, item.id)}
                        />
                      </Box>
                    ))}
                  </Box>
                </Box>
              );
            })}
          </>
        )}
      </ScrollView>

      {!isAdding && listId && (
        <Box position="absolute" bottom={24} left={24} right={24}>
          <Button
            size="lg"
            borderRadius="$full"
            shadowColor="$black"
            shadowOffset={{ width: 0, height: 4 }}
            shadowOpacity={0.15}
            shadowRadius={8}
            onPress={() => {
              Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
              setIsAdding(true);
            }}
            style={{ backgroundColor: "#16a34a" }}
          >
            <ButtonText color="$white" bold>+ Add Item</ButtonText>
          </Button>
        </Box>
      )}
    </SafeAreaView>
  );
}
