import { ScrollView, ActivityIndicator, Pressable } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Box, Text, VStack, HStack, Input, InputField, InputSlot, InputIcon, SearchIcon, Button, ButtonText, Icon } from "@gluestack-ui/themed";
import { useState } from "react";
import { useRouter } from "expo-router";
import { apiRequest } from "../../src/api/client";

type RecipeResult = {
  title: string;
  ingredients: string[];
  all_ingredients?: string[];
  directions?: string;
  semantic_score: number;
  overlap_score: number;
  combined_score: number;
  rank: number;
  tags?: {
    vegan: boolean;
    vegetarian: boolean;
    gluten_free: boolean;
    dairy_free: boolean;
  };
};

const categories = ["All", "Breakfast", "Lunch", "Dinner", "Snacks", "Vegan"];

export default function RecipesScreen() {
  const [recipes, setRecipes] = useState<RecipeResult[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [selectedCat, setSelectedCat] = useState("All");
  const router = useRouter();

  const handleSearch = async () => {
    const ingredients = query.split(",").map((i) => i.trim()).filter(Boolean);
    if (ingredients.length === 0) return;
    setLoading(true);
    setSearched(true);
    try {
      const data = await apiRequest<RecipeResult[]>("/suggest_recipes", {
        method: "POST",
        body: { ingredients, top_n: 5, rerank_weight: 0.6 },
      });
      setRecipes(data);
    } catch (e: any) {
      console.log("Failed to load recipes", e?.message || e);
      setRecipes([]);
    } finally {
      setLoading(false);
    }
  };

  const ingredientChips = query.split(",").map(i => i.trim()).filter(Boolean);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#FAFAFA' }} edges={["top", "left", "right"]}>
      <Box px="$6" py="$4">
        <Text color="$coolGray400" fontWeight="$medium">Find your next meal</Text>
        <Text size="3xl" bold color="$coolGray900" mt="$1">Discover Recipes</Text>
      </Box>

      {/* Search Bar */}
      <Box px="$6" mb="$4">
        <HStack space="sm">
          <Input variant="outline" size="lg" flex={1} bg="$white" borderRadius="$xl" borderColor="$coolGray200">
            <InputSlot pl="$3">
              <InputIcon as={SearchIcon} color="$coolGray400" />
            </InputSlot>
            <InputField
              placeholder="e.g. chicken, tomato, garlic"
              value={query}
              onChangeText={setQuery}
              onSubmitEditing={handleSearch}
              returnKeyType="search"
            />
          </Input>
          <Button bg="$green600" borderRadius="$xl" px="$5" h="$12" onPress={handleSearch}>
            <ButtonText color="$white" bold>Search</ButtonText>
          </Button>
        </HStack>
      </Box>

      {/* Ingredient Chips Preview */}
      {ingredientChips.length > 0 && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingLeft: 24, paddingRight: 24, marginBottom: 12 }}>
          <HStack space="xs">
            {ingredientChips.map((chip, i) => (
              <Box key={i} px="$3" py="$1" bg="$green100" borderRadius="$full">
                <Text size="sm" color="$green700">{chip}</Text>
              </Box>
            ))}
          </HStack>
        </ScrollView>
      )}

      {/* Category Filters */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingLeft: 24, paddingRight: 24, marginBottom: 16 }}>
        <HStack space="sm">
          {categories.map((cat) => (
            <Box key={cat}>
              <Pressable
                onPress={() => setSelectedCat(cat)}
                style={{
                  paddingHorizontal: 16,
                  paddingVertical: 8,
                  borderRadius: 20,
                  backgroundColor: cat === selectedCat ? "#16a34a" : "#ffffff",
                  borderWidth: 1,
                  borderColor: cat === selectedCat ? "#16a34a" : "#e5e7eb",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Text
                  color={cat === selectedCat ? "$white" : "$coolGray500"}
                  bold={cat === selectedCat}
                  size="xs"
                >
                  {cat}
                </Text>
              </Pressable>
            </Box>
          ))}
        </HStack>
      </ScrollView>

      {/* Results */}
      <ScrollView contentContainerStyle={{ paddingHorizontal: 24, paddingBottom: 100 }}>

        {/* Loading State */}
        {loading && (
          <Box alignItems="center" py="$10">
            <ActivityIndicator size="large" color="#16a34a" />
            <Text color="$coolGray500" mt="$4">Finding recipes...</Text>
          </Box>
        )}

        {/* Empty State - Before Search */}
        {!searched && !loading && (
          <Box alignItems="center" py="$10">
            <Text size="4xl" mb="$4">🍳</Text>
            <Text size="lg" bold color="$coolGray900" mb="$2">What's in your kitchen?</Text>
            <Text color="$coolGray500" textAlign="center" px="$4">
              Type ingredients separated by commas and tap Search to discover recipes you can make.
            </Text>
          </Box>
        )}

        {/* Empty State - After Search */}
        {searched && !loading && recipes.length === 0 && (
          <Box alignItems="center" py="$10">
            <Text size="4xl" mb="$4">🔍</Text>
            <Text size="lg" bold color="$coolGray900" mb="$2">No recipes found</Text>
            <Text color="$coolGray500" textAlign="center" px="$4">
              Try different ingredients or check that the backend server is running.
            </Text>
          </Box>
        )}

        {/* Recipe Results */}
        {!loading && recipes.length > 0 && (
          <>
            <Text size="lg" bold color="$coolGray900" mb="$4">
              Found {recipes.length} recipe{recipes.length !== 1 ? "s" : ""}
            </Text>

            {recipes.map((recipe, index) => (
              <Box key={`${recipe.rank}-${recipe.title}`} bg="$white" borderRadius="$2xl" overflow="hidden" mb="$5" borderWidth={1} borderColor="$coolGray100" shadowColor="$black" shadowOffset={{ width: 0, height: 2 }} shadowOpacity={0.05} shadowRadius={4}>
                <Box h={120} bg={
                  index % 4 === 0 ? "$green400" :
                    index % 4 === 1 ? "$orange400" :
                      index % 4 === 2 ? "$yellow400" : "$blue400"
                } alignItems="center" justifyContent="center" px="$4">
                  <Text color="$white" size="xl" bold textAlign="center" numberOfLines={2}>{recipe.title}</Text>
                </Box>
                <Box p="$4">
                  <HStack justifyContent="space-between" alignItems="center" mb="$3">
                    <HStack space="sm" flexWrap="wrap">
                      <Box px="$2" py="$1" bg="$green100" borderRadius="$md" mb="$1">
                        <Text size="xs" color="$green700" bold>Match: {(recipe.combined_score * 100).toFixed(0)}%</Text>
                      </Box>
                      <Box px="$2" py="$1" bg="$green100" borderRadius="$md" mb="$1">
                        <Text size="xs" color="$green700">Overlap: {(recipe.overlap_score * 100).toFixed(0)}%</Text>
                      </Box>
                      <Box px="$2" py="$1" bg="$coolGray100" borderRadius="$md" mb="$1">
                        <Text size="xs" color="$coolGray700">#{recipe.rank}</Text>
                      </Box>
                    </HStack>
                  </HStack>

                  {/* Matching Ingredients */}
                  {recipe.ingredients && recipe.ingredients.length > 0 && (
                    <Box mb="$3">
                      <Text size="xs" color="$coolGray500" mb="$1">Matching Ingredients:</Text>
                      <HStack flexWrap="wrap" space="xs">
                        {recipe.ingredients.map((ing, i) => (
                          <Box key={i} px="$2" py="$0.5" bg="$green100" borderRadius="$full" mb="$1">
                            <Text size="xs" color="$green700">{ing}</Text>
                          </Box>
                        ))}
                      </HStack>
                    </Box>
                  )}

                  <Button
                    size="sm"
                    bg="$green600"
                    borderRadius="$full"
                    onPress={() => {
                      router.push({
                        pathname: "/recipe-detail",
                        params: {
                          title: recipe.title,
                          matchScore: String(recipe.combined_score),
                          ingredients: recipe.ingredients.join(","),
                          all_ingredients: recipe.all_ingredients?.join(",") || recipe.ingredients.join(","),
                          directions: recipe.directions || "Directions coming soon...",
                          pantry: query, // Pass user's search ingredients as their "pantry"
                          tags: recipe.tags ? JSON.stringify(recipe.tags) : "",
                        },
                      });
                    }}
                  >
                    <ButtonText color="$white" bold>View Recipe</ButtonText>
                  </Button>
                </Box>
              </Box>
            ))}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
