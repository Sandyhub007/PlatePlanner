import { useState, useCallback } from "react";
import {
  ScrollView,
  ActivityIndicator,
  TextInput,
  TouchableOpacity,
  ImageBackground,
} from "react-native";
import { Box, Text, VStack, HStack } from "@gluestack-ui/themed";
import { LinearGradient } from "expo-linear-gradient";
import { useFocusEffect } from "expo-router";
import { useAuth } from "../../src/state/auth";
import { apiRequest } from "../../src/api/client";

type PantryItem = { name: string; created_at: string };
type PantryResponse = { items: PantryItem[] };

export default function PantryScreen() {
  const { token } = useAuth();
  const [items, setItems] = useState<PantryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [inputText, setInputText] = useState("");
  const [adding, setAdding] = useState(false);

  const fetchPantry = useCallback(async () => {
    if (!token) return;
    try {
      setLoading(true);
      const data = await apiRequest<PantryResponse>("/pantry", { token });
      setItems(data.items);
    } catch (e) {
      if (__DEV__) console.log("Failed to load pantry", e);
    } finally {
      setLoading(false);
    }
  }, [token]);

  // Refresh whenever the tab becomes focused
  useFocusEffect(
    useCallback(() => {
      fetchPantry();
    }, [fetchPantry])
  );

  const handleAdd = async () => {
    const names = inputText
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (names.length === 0) return;
    try {
      setAdding(true);
      const data = await apiRequest<PantryResponse>("/pantry/items", {
        token,
        method: "POST",
        body: { items: names },
      });
      setItems(data.items);
      setInputText("");
    } catch (e) {
      if (__DEV__) console.log("Failed to add pantry items", e);
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (name: string) => {
    try {
      await apiRequest(`/pantry/items/${encodeURIComponent(name)}`, {
        token,
        method: "DELETE",
      });
      setItems((prev) => prev.filter((i) => i.name !== name));
    } catch (e) {
      if (__DEV__) console.log("Failed to delete pantry item", e);
    }
  };

  return (
    <Box style={{ flex: 1, backgroundColor: "#FAFAFA" }}>
      {/* Header */}
      <ImageBackground
        source={{
          uri: "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=800&q=80",
        }}
        style={{ width: "100%", paddingTop: 60, paddingBottom: 30 }}
        imageStyle={{ opacity: 0.85 }}
      >
        <LinearGradient
          colors={["rgba(0,0,0,0.7)", "rgba(0,0,0,0.25)"]}
          style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }}
        />
        <Box px="$6" mb="$4">
          <Text color="$coolGray200" fontWeight="$medium">
            What's in your fridge?
          </Text>
          <Text size="3xl" bold color="$white" mt="$1">
            My Pantry
          </Text>
        </Box>

        {/* Add input */}
        <Box px="$6">
          <HStack space="sm">
            <Box
              flex={1}
              bg="$white"
              borderRadius="$xl"
              borderWidth={1}
              borderColor="$coolGray200"
              px="$4"
              h={48}
              justifyContent="center"
            >
              <TextInput
                placeholder="garlic, olive oil, tomato..."
                placeholderTextColor="#9ca3af"
                value={inputText}
                onChangeText={setInputText}
                onSubmitEditing={handleAdd}
                returnKeyType="done"
                style={{ fontSize: 15, color: "#111827" }}
                accessibilityLabel="Add pantry ingredients"
                accessibilityHint="Enter ingredient names separated by commas"
              />
            </Box>
            <TouchableOpacity
              onPress={handleAdd}
              disabled={adding}
              accessibilityLabel="Add ingredients to pantry"
              accessibilityRole="button"
              style={{
                backgroundColor: "#16a34a",
                borderRadius: 12,
                paddingHorizontal: 20,
                height: 48,
                alignItems: "center",
                justifyContent: "center",
                opacity: adding ? 0.6 : 1,
              }}
            >
              {adding ? (
                <ActivityIndicator color="white" size="small" />
              ) : (
                <Text color="$white" bold>
                  Add
                </Text>
              )}
            </TouchableOpacity>
          </HStack>
          <Text color="$coolGray300" size="xs" mt="$2">
            Separate multiple items with commas
          </Text>
        </Box>
      </ImageBackground>

      {/* Item count badge */}
      {items.length > 0 && (
        <Box px="$6" py="$3">
          <Text size="sm" color="$coolGray500">
            {items.length} ingredient{items.length !== 1 ? "s" : ""} saved
          </Text>
        </Box>
      )}

      {/* Content */}
      <ScrollView contentContainerStyle={{ paddingHorizontal: 24, paddingBottom: 120 }}>
        {loading && (
          <Box alignItems="center" py="$10">
            <ActivityIndicator size="large" color="#16a34a" />
            <Text color="$coolGray500" mt="$4">
              Loading pantry...
            </Text>
          </Box>
        )}

        {!loading && !token && (
          <Box alignItems="center" py="$10">
            <Text size="4xl" mb="$4">🔒</Text>
            <Text size="lg" bold color="$coolGray900" mb="$2">
              Sign in required
            </Text>
            <Text color="$coolGray500" textAlign="center">
              Sign in to save and manage your pantry ingredients.
            </Text>
          </Box>
        )}

        {!loading && token && items.length === 0 && (
          <Box alignItems="center" py="$10">
            <Text size="4xl" mb="$4">🫙</Text>
            <Text size="lg" bold color="$coolGray900" mb="$2">
              Your pantry is empty
            </Text>
            <Text color="$coolGray500" textAlign="center" px="$4">
              Add ingredients above and they'll automatically be used when checking recipe compatibility.
            </Text>
          </Box>
        )}

        {!loading && items.length > 0 && (
          <Box bg="$white" borderRadius="$2xl" overflow="hidden" mt="$2"
            shadowColor="$black" shadowOffset={{ width: 0, height: 2 }}
            shadowOpacity={0.05} shadowRadius={4}
            borderWidth={1} borderColor="$coolGray100">
            <VStack>
              {items.map((item, i) => (
                <HStack
                  key={item.name}
                  alignItems="center"
                  px="$4"
                  py="$3"
                  borderBottomWidth={i < items.length - 1 ? 1 : 0}
                  borderBottomColor="$coolGray100"
                >
                  {/* Green dot */}
                  <Box
                    w={10}
                    h={10}
                    borderRadius="$full"
                    bg="$green500"
                    mr="$3"
                  />
                  <Text
                    flex={1}
                    color="$coolGray800"
                    size="md"
                    textTransform="capitalize"
                  >
                    {item.name}
                  </Text>
                  <TouchableOpacity
                    onPress={() => handleDelete(item.name)}
                    hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
                    accessibilityLabel={`Remove ${item.name} from pantry`}
                    accessibilityRole="button"
                  >
                    <Box
                      w={28}
                      h={28}
                      borderRadius="$full"
                      bg="$red50"
                      alignItems="center"
                      justifyContent="center"
                    >
                      <Text size="xs" color="$red500" bold>✕</Text>
                    </Box>
                  </TouchableOpacity>
                </HStack>
              ))}
            </VStack>
          </Box>
        )}
      </ScrollView>
    </Box>
  );
}
