export type TokenResponse = {
  access_token: string;
  token_type: string;
};

export type User = {
  id: string;
  email: string;
  full_name?: string | null;
  is_active: boolean;
  is_premium: boolean;
  auth_provider: string; // "email" or "google"
  profile_photo_url?: string | null;
  created_at: string;
  preferences?: UserPreferences | null;
};

export type UserPreferences = {
  id: string;
  user_id: string;
  dietary_restrictions: string[];
  allergies: string[];
  cuisine_preferences: string[];
  calorie_target?: number | null;
  protein_target?: number | null;
  carb_target?: number | null;
  fat_target?: number | null;
  cooking_time_max?: number | null;
  budget_per_week?: number | null;
  people_count: number;
};

export type NutritionSummary = {
  daily_averages: {
    calories: number;
    protein_g: number;
    carbs_g: number;
    fat_g: number;
  };
  macro_distribution?: {
    protein_pct: number;
    carbs_pct: number;
    fat_pct: number;
  };
};

export type RecipeSuggestion = {
  title: string;
  combined_score: number;
  rank: number;
};

export type MealPlanItem = {
  id: string;
  day_of_week: number;
  meal_type: string;
  recipe_title: string;
};

export type MealPlan = {
  id: string;
  week_start_date: string;
  week_end_date: string;
  items: MealPlanItem[];
};

export type ShoppingListSummary = {
  id: string;
  name: string;
  total_items: number;
  purchased_items: number;
  status: string;
};

export type ShoppingListWithCategories = {
  id: string;
  name: string;
  items_by_category: Record<
    string,
    { id: string; item_name: string; quantity: number; unit?: string | null }[]
  >;
};
