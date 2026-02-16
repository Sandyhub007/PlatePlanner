import { useLocalSearchParams, useRouter } from 'expo-router';
import { Box, Text, ScrollView, Button, ButtonText, HStack, VStack, Icon, ArrowLeftIcon } from '@gluestack-ui/themed';
import { ActivityIndicator, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useEffect, useState } from 'react';
import { apiRequest } from '../src/api/client';

// Types
type RecipeDetails = {
  title: string;
  directions: string[];
  ingredients: string[];
  link: string;
  source: string;
};

type PantrySubItem = {
  name: string;
  score: number;
  source: string;
};

type MissingIngredient = {
  ingredient: string;
  pantry_substitutes: PantrySubItem[];
  other_substitutes: PantrySubItem[];
};

type HaveIngredient = {
  ingredient: string;
  matched_as: string;
};

type SubstitutionData = {
  recipe_title: string;
  total_ingredients: number;
  have_count: number;
  missing_count: number;
  coverage: number;
  have: HaveIngredient[];
  missing: MissingIngredient[];
};

// Response from GET /substitute
type SubstituteApiItem = {
  name: string;
  score: number;
  context: string | null;
  source: string;
};

type SubstituteApiResponse = {
  ingredient: string;
  context: string | null;
  hybrid: boolean;
  substitutes: SubstituteApiItem[];
};

// Per-ingredient on-demand search state
type SearchedSubResult = {
  loading: boolean;
  searched: boolean;
  inPantry: SubstituteApiItem[];
  other: SubstituteApiItem[];
  error: boolean;
};

export default function RecipeDetailScreen() {
  const params = useLocalSearchParams();
  const router = useRouter();

  const title = typeof params.title === 'string' ? params.title : "";
  const matchScore = typeof params.matchScore === 'string' ? params.matchScore : "0";
  const initialIngredients = typeof params.ingredients === 'string' ? params.ingredients.split(',') : [];
  const pantryRaw = typeof params.pantry === 'string' ? params.pantry : "";
  const tagsRaw = typeof params.tags === 'string' ? params.tags : "";

  const pantryItems = pantryRaw.split(",").map(i => i.trim()).filter(Boolean);
  const pantryLower = new Set(pantryItems.map(p => p.toLowerCase()));

  let tags: { vegan?: boolean; vegetarian?: boolean; gluten_free?: boolean; dairy_free?: boolean } = {};
  try {
    if (tagsRaw) tags = JSON.parse(tagsRaw);
  } catch { }

  const [details, setDetails] = useState<RecipeDetails | null>(null);
  const [subData, setSubData] = useState<SubstitutionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [subLoading, setSubLoading] = useState(false);
  const [error, setError] = useState(false);

  // Per-ingredient on-demand search results (keyed by ingredient name)
  const [searchResults, setSearchResults] = useState<Record<string, SearchedSubResult>>({});

  // Fetch recipe details
  useEffect(() => {
    if (!title) return;
    const fetchDetails = async () => {
      try {
        setLoading(true);
        const encodedTitle = encodeURIComponent(title);
        const data = await apiRequest<RecipeDetails>(`/recipes/${encodedTitle}`);
        setDetails(data);
      } catch (err) {
        console.log("Failed to fetch details", err);
        setError(true);
      } finally {
        setLoading(false);
      }
    };
    fetchDetails();
  }, [title]);

  // Fetch substitution data (only if pantry is available)
  useEffect(() => {
    if (!title || pantryItems.length === 0) return;
    const fetchSubs = async () => {
      try {
        setSubLoading(true);
        const encodedTitle = encodeURIComponent(title);
        const data = await apiRequest<SubstitutionData>(
          `/recipes/${encodedTitle}/substitutions`,
          {
            method: "POST",
            body: { pantry: pantryItems },
          }
        );
        setSubData(data);
      } catch (err) {
        console.log("Failed to fetch substitutions", err);
      } finally {
        setSubLoading(false);
      }
    };
    fetchSubs();
  }, [title]);

  // Fuzzy match: check if a substitute name matches anything in pantry
  const isInPantry = (name: string): boolean => {
    const nameLower = name.toLowerCase().replace(/_/g, ' ');
    for (const p of pantryLower) {
      if (p.includes(nameLower) || nameLower.includes(p)) return true;
    }
    return false;
  };

  // On-demand search for substitutes for a specific missing ingredient
  const searchSubstitutes = async (ingredient: string) => {
    setSearchResults(prev => ({
      ...prev,
      [ingredient]: { loading: true, searched: false, inPantry: [], other: [], error: false },
    }));

    try {
      const encoded = encodeURIComponent(ingredient);
      const data = await apiRequest<SubstituteApiResponse>(
        `/substitute?ingredient=${encoded}&hybrid=true&top_k=8`
      );

      // Split results: those in pantry vs not
      const inPantry: SubstituteApiItem[] = [];
      const other: SubstituteApiItem[] = [];
      for (const sub of data.substitutes) {
        if (isInPantry(sub.name)) {
          inPantry.push(sub);
        } else {
          other.push(sub);
        }
      }

      setSearchResults(prev => ({
        ...prev,
        [ingredient]: { loading: false, searched: true, inPantry, other, error: false },
      }));
    } catch (err) {
      console.log(`Failed to search substitutes for ${ingredient}`, err);
      setSearchResults(prev => ({
        ...prev,
        [ingredient]: { loading: false, searched: true, inPantry: [], other: [], error: true },
      }));
    }
  };

  const score = parseFloat(matchScore);
  const displayIngredients = details?.ingredients && details.ingredients.length > 0
    ? details.ingredients
    : initialIngredients;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#FAFAFA' }} edges={['top', 'left', 'right']}>
      <ScrollView contentContainerStyle={{ paddingBottom: 40 }}>
        {/* Header Banner */}
        <Box h={250} bg="$green600" justifyContent="center" alignItems="center">
          <Box position="absolute" top={16} left={16} zIndex={10}>
            <Button onPress={() => router.back()} variant="solid" bg="rgba(0,0,0,0.3)" borderRadius="$full" w={40} h={40} p={0}>
              <Icon as={ArrowLeftIcon} color="white" />
            </Button>
          </Box>
          <Text color="white" opacity={0.5} size="4xl" bold>Food Image</Text>
        </Box>

        <Box px="$6" py="$6" mt="-$6" bg="#FAFAFA" borderTopLeftRadius="$3xl" borderTopRightRadius="$3xl">
          <Text size="2xl" bold color="$coolGray900" mb="$2" lineHeight={34}>{title}</Text>

          {/* Tags Row */}
          <HStack space="md" mb="$6" flexWrap="wrap">
            <Box px="$3" py="$1" bg="$green100" borderRadius="$md">
              <Text color="$green700" bold>Match: {(score * 100).toFixed(0)}%</Text>
            </Box>
            {tags.vegan && (
              <Box px="$3" py="$1" bg="$green100" borderRadius="$md">
                <Text color="$green700" bold>🌱 Vegan</Text>
              </Box>
            )}
            {tags.vegetarian && !tags.vegan && (
              <Box px="$3" py="$1" bg="$green100" borderRadius="$md">
                <Text color="$green700" bold>🥬 Vegetarian</Text>
              </Box>
            )}
            {tags.gluten_free && (
              <Box px="$3" py="$1" bg="$blue100" borderRadius="$md">
                <Text color="$blue700" bold>🚫 Gluten-Free</Text>
              </Box>
            )}
            {tags.dairy_free && (
              <Box px="$3" py="$1" bg="$purple100" borderRadius="$md">
                <Text color="$purple700" bold>🥛 Dairy-Free</Text>
              </Box>
            )}
          </HStack>

          {/* Coverage Bar */}
          {subData && (
            <Box mb="$6" bg="$white" p="$4" borderRadius="$xl"
              shadowColor="$black" shadowOffset={{ width: 0, height: 1 }} shadowOpacity={0.05} shadowRadius={2}>
              <HStack justifyContent="space-between" alignItems="center" mb="$2">
                <Text size="md" bold color="$coolGray900">Pantry Coverage</Text>
                <Text size="md" bold color={subData.coverage >= 0.7 ? "$green600" : subData.coverage >= 0.4 ? "$orange500" : "$red500"}>
                  {(subData.coverage * 100).toFixed(0)}%
                </Text>
              </HStack>
              <Box h={8} bg="$coolGray100" borderRadius="$full" overflow="hidden">
                <Box
                  h={8}
                  borderRadius="$full"
                  bg={subData.coverage >= 0.7 ? "$green500" : subData.coverage >= 0.4 ? "$orange400" : "$red400"}
                  w={`${Math.min(subData.coverage * 100, 100)}%` as any}
                />
              </Box>
              <HStack justifyContent="space-between" mt="$1">
                <Text size="xs" color="$coolGray400">✅ {subData.have_count} have</Text>
                <Text size="xs" color="$coolGray400">❌ {subData.missing_count} missing</Text>
              </HStack>
            </Box>
          )}

          {/* Ingredients Section */}
          <Box mb="$6">
            <Text size="xl" bold color="$coolGray900" mb="$3">Ingredients</Text>

            {subLoading && (
              <HStack space="sm" alignItems="center" mb="$3">
                <ActivityIndicator size="small" color="#16a34a" />
                <Text color="$coolGray500" size="sm">Checking your pantry...</Text>
              </HStack>
            )}

            <VStack space="sm" bg="$white" p="$4" borderRadius="$xl"
              shadowColor="$black" shadowOffset={{ width: 0, height: 1 }} shadowOpacity={0.05} shadowRadius={2}>

              {subData ? (
                <>
                  {/* Ingredients user HAS */}
                  {subData.have.map((item, i) => (
                    <HStack key={`have-${i}`} alignItems="center" space="sm" py="$1">
                      <Box w={24} h={24} borderRadius="$full" bg="$green500" alignItems="center" justifyContent="center">
                        <Text color="white" size="xs" bold>✓</Text>
                      </Box>
                      <Text color="$coolGray700" size="md" textTransform="capitalize" flex={1}>
                        {item.ingredient}
                      </Text>
                      <Box px="$2" py="$0.5" bg="$green50" borderRadius="$full">
                        <Text size="xs" color="$green600">In pantry</Text>
                      </Box>
                    </HStack>
                  ))}

                  {/* Ingredients user is MISSING */}
                  {subData.missing.map((item, i) => {
                    const result = searchResults[item.ingredient];
                    return (
                      <Box key={`miss-${i}`} py="$1">
                        {/* Ingredient row */}
                        <HStack alignItems="center" space="sm">
                          <Box w={24} h={24} borderRadius="$full" bg="$red400" alignItems="center" justifyContent="center">
                            <Text color="white" size="xs" bold>✗</Text>
                          </Box>
                          <Text color="$coolGray700" size="md" textTransform="capitalize" flex={1}>
                            {item.ingredient}
                          </Text>
                          <Box px="$2" py="$0.5" bg="$red50" borderRadius="$full">
                            <Text size="xs" color="$red500">Missing</Text>
                          </Box>
                        </HStack>

                        {/* Search for Substitutes button — shown only before search */}
                        {!result?.searched && !result?.loading && (
                          <TouchableOpacity
                            onPress={() => searchSubstitutes(item.ingredient)}
                            activeOpacity={0.7}
                          >
                            <HStack
                              ml="$8" mt="$2" px="$3" py="$2"
                              bg="$green50" borderRadius="$lg"
                              borderWidth={1} borderColor="$green200"
                              alignItems="center" justifyContent="center"
                              space="sm"
                            >
                              <Text size="sm" color="$green600" bold>🔍 Search for Substitutes</Text>
                            </HStack>
                          </TouchableOpacity>
                        )}

                        {/* Loading spinner while searching */}
                        {result?.loading && (
                          <HStack ml="$8" mt="$2" space="sm" alignItems="center" py="$1">
                            <ActivityIndicator size="small" color="#16a34a" />
                            <Text size="sm" color="$coolGray500">
                              Searching substitutes for {item.ingredient}...
                            </Text>
                          </HStack>
                        )}

                        {/* Search results */}
                        {result?.searched && !result?.loading && (
                          <Box ml="$8" mt="$2" pl="$3" borderLeftWidth={2} borderLeftColor="$green200">

                            {/* Error state with retry */}
                            {result.error && (
                              <HStack space="sm" alignItems="center" py="$1">
                                <Text size="xs" color="$red500">
                                  Could not find substitutes.
                                </Text>
                                <TouchableOpacity onPress={() => searchSubstitutes(item.ingredient)}>
                                  <Text size="xs" color="$green600" bold>Retry</Text>
                                </TouchableOpacity>
                              </HStack>
                            )}

                            {/* Pantry matches — highlighted prominently */}
                            {result.inPantry.length > 0 && (
                              <Box mb="$2">
                                <Text size="xs" color="$green600" bold mb="$1">
                                  🎯 In your pantry:
                                </Text>
                                {result.inPantry.map((sub, si) => (
                                  <HStack key={si} alignItems="center" space="sm" py="$1"
                                    bg="$green50" px="$2" borderRadius="$md" mb="$1">
                                    <Box w={10} h={10} borderRadius="$full" bg="$green400" />
                                    <Text size="sm" color="$green700" bold textTransform="capitalize" flex={1}>
                                      {sub.name.replace(/_/g, ' ')}
                                    </Text>
                                    <Box px="$2" py="$0.5" bg="$green100" borderRadius="$full">
                                      <Text size="xs" color="$green700">
                                        {(sub.score * 100).toFixed(0)}% match
                                      </Text>
                                    </Box>
                                  </HStack>
                                ))}
                              </Box>
                            )}

                            {/* Other substitutes (not in pantry) */}
                            {result.other.length > 0 && (
                              <Box mb="$1">
                                <Text size="xs" color="$coolGray500" bold mb="$1">
                                  🛒 Other options:
                                </Text>
                                {result.other.slice(0, 4).map((sub, si) => (
                                  <HStack key={si} alignItems="center" space="sm" py="$0.5">
                                    <Box w={8} h={8} borderRadius="$full" bg="$coolGray300" />
                                    <Text size="sm" color="$coolGray500" textTransform="capitalize" flex={1}>
                                      {sub.name.replace(/_/g, ' ')}
                                    </Text>
                                    <Text size="xs" color="$coolGray400">
                                      {(sub.score * 100).toFixed(0)}%
                                    </Text>
                                  </HStack>
                                ))}
                              </Box>
                            )}

                            {/* No results found */}
                            {!result.error && result.inPantry.length === 0 && result.other.length === 0 && (
                              <Text size="xs" color="$coolGray400" fontStyle="italic" py="$1">
                                No substitutes found for this ingredient.
                              </Text>
                            )}
                          </Box>
                        )}
                      </Box>
                    );
                  })}
                </>
              ) : (
                /* Fallback: plain ingredient list (no pantry was provided) */
                displayIngredients.length > 0 ? (
                  displayIngredients.map((ing, i) => (
                    <HStack key={i} alignItems="center" space="sm">
                      <Box w={6} h={6} borderRadius="$full" bg="$green500" alignItems="center" justifyContent="center">
                        <Icon as={ArrowLeftIcon} color="white" size="xs" style={{ transform: [{ rotate: '-45deg' }] }} />
                      </Box>
                      <Text color="$coolGray700" size="md" textTransform="capitalize">{ing}</Text>
                    </HStack>
                  ))
                ) : (
                  <Text color="$coolGray500">No ingredients information found.</Text>
                )
              )}
            </VStack>
          </Box>

          {/* Directions Section */}
          <Box mb="$6">
            <Text size="xl" bold color="$coolGray900" mb="$3">Directions</Text>
            <Box bg="$white" p="$4" borderRadius="$xl"
              shadowColor="$black" shadowOffset={{ width: 0, height: 1 }} shadowOpacity={0.05} shadowRadius={2}>
              {loading ? (
                <HStack space="sm" alignItems="center">
                  <ActivityIndicator size="small" color="#16a34a" />
                  <Text color="$coolGray500">Loading directions...</Text>
                </HStack>
              ) : error ? (
                <Text color="$red500">Could not load directions. Please try again later.</Text>
              ) : details?.directions && details.directions.length > 0 ? (
                <VStack space="md">
                  {details.directions.map((step, i) => (
                    <HStack key={i} space="sm">
                      <Text bold color="$green600">{i + 1}.</Text>
                      <Text color="$coolGray700" flex={1}>{step}</Text>
                    </HStack>
                  ))}
                </VStack>
              ) : (
                <Text color="$coolGray500" fontStyle="italic">
                  Full instructions are not available for this recipe.
                </Text>
              )}
            </Box>
          </Box>
        </Box>
      </ScrollView>
    </SafeAreaView>
  );
}
