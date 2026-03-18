# PlatePlanner - Store Listing Information

This document contains all the metadata and assets needed for Google Play Store and Apple App Store submissions.

---

## General App Information

| Field               | Value                                                        |
| ------------------- | ------------------------------------------------------------ |
| App Name            | PlatePlanner                                                 |
| Bundle ID (iOS)     | com.plateplanner.app                                         |
| Package Name (Android) | com.plateplanner.app                                      |
| Category            | Food & Drink                                                 |
| Content Rating      | Everyone / 4+                                                |
| Default Language    | English (US)                                                 |
| Privacy Policy URL  | https://plateplanner.app/privacy (TODO: create this page)    |
| Terms of Service URL| https://plateplanner.app/terms (TODO: create this page)      |
| Support URL         | https://plateplanner.app/support (TODO: create this page)    |
| Support Email       | support@plateplanner.app                                     |

---

## Short Description (max 80 characters)

> Plan meals, discover recipes, track nutrition, and manage your grocery list.

---

## Full Description (max 4000 characters)

PlatePlanner is your all-in-one meal planning and nutrition companion. Whether you are trying to eat healthier, plan meals for the week, or simplify grocery shopping, PlatePlanner makes it effortless.

**Key Features:**

- Personalized Meal Plans -- Get weekly meal plans tailored to your dietary preferences, calorie goals, and nutritional needs.
- Smart Recipe Discovery -- Browse thousands of recipes with detailed nutrition info. Filter by cuisine, dietary restrictions, prep time, and ingredients.
- Nutrition Tracking -- Log your meals and track macronutrients (calories, protein, carbs, fat) with easy-to-read dashboards and progress charts.
- Shopping List -- Automatically generate organized grocery lists from your meal plan. Check off items as you shop.
- Pantry Management -- Track what you already have at home to reduce food waste and get recipe suggestions based on available ingredients.
- Meal Photo Logging -- Snap photos of your meals to keep a visual food diary.
- Dietary Preferences -- Support for vegetarian, vegan, gluten-free, keto, paleo, and more.

**Why PlatePlanner?**

Eating well should not be complicated. PlatePlanner removes the guesswork from meal planning and helps you build sustainable, healthy eating habits. Whether you are cooking for one or feeding a family, PlatePlanner adapts to your lifestyle.

Download PlatePlanner today and take the stress out of meal planning.

---

## Keywords (iOS - max 100 characters, comma-separated)

```
meal planner,recipes,nutrition,calorie tracker,grocery list,diet,food,meal prep,healthy eating,pantry
```

---

## Google Play Store Tags

- Meal Planning
- Recipe Manager
- Nutrition Tracker
- Calorie Counter
- Grocery List
- Diet Planner
- Food Diary
- Healthy Eating

---

## Required Screenshots

### Phone Screenshots (required for both stores)

All screenshots should be **1290 x 2796 px** (iPhone 15 Pro Max / 6.7" display) for iOS, and **1080 x 2400 px** for Android. Minimum 2, recommended 5-8.

| # | Screen          | Description                                                 | Status  |
|---|-----------------|-------------------------------------------------------------|---------|
| 1 | Home / Dashboard | Weekly meal plan overview with nutrition summary            | TODO    |
| 2 | Recipe Discovery | Browse recipes with filters and search                     | TODO    |
| 3 | Recipe Detail    | Full recipe view with ingredients, steps, and nutrition     | TODO    |
| 4 | Meal Logging     | Nutrition tracking dashboard with daily/weekly charts       | TODO    |
| 5 | Shopping List    | Organized grocery list with categories and checkmarks       | TODO    |
| 6 | Pantry           | Pantry inventory management screen                          | TODO    |
| 7 | Meal Plan Setup  | Dietary preferences and goal setting                        | TODO    |
| 8 | Profile          | User profile with nutrition goals and achievements          | TODO    |

### Tablet Screenshots (optional but recommended for iPad)

- Same screens as phone, at **2048 x 2732 px** (12.9" iPad Pro)

---

## App Icon

| Asset                    | Size         | Status |
| ------------------------ | ------------ | ------ |
| iOS App Icon             | 1024 x 1024  | TODO   |
| Android Adaptive Icon    | 1024 x 1024  | TODO   |
| Android Foreground Layer | 1024 x 1024  | TODO   |
| Play Store Hi-res Icon   | 512 x 512    | TODO   |

---

## Feature Graphic (Google Play - required)

- Size: **1024 x 500 px**
- Should showcase the app name, key visual, and value proposition
- Status: TODO

---

## Promotional Video (optional but recommended)

- YouTube link for Google Play
- App Preview video for iOS (15-30 seconds)
- Status: TODO

---

## App Review Information (Apple)

| Field                 | Value                                     |
| --------------------- | ----------------------------------------- |
| Demo Account Email    | demo@plateplanner.app                     |
| Demo Account Password | (set a demo password before submission)   |
| Review Notes          | This app requires an account to use. A demo account is provided above. The app connects to our API server for meal plans, recipes, and nutrition data. |

---

## Data Safety / Privacy (Google Play)

| Question                                         | Answer                              |
| ------------------------------------------------ | ----------------------------------- |
| Does the app collect or share user data?         | Yes - collects                      |
| Data types collected                             | Name, email, food preferences, meal logs, photos |
| Is data encrypted in transit?                    | Yes (HTTPS)                         |
| Can users request data deletion?                 | Yes                                 |
| Is data shared with third parties?               | No                                  |

---

## App Privacy (Apple - App Tracking Transparency)

| Category              | Data Collected                          | Linked to User | Used for Tracking |
| --------------------- | --------------------------------------- | --------------- | ----------------- |
| Contact Info          | Email address                           | Yes             | No                |
| Health & Fitness      | Nutrition/calorie data                  | Yes             | No                |
| User Content          | Meal photos, recipes                    | Yes             | No                |
| Identifiers           | User ID                                 | Yes             | No                |

---

## Release Checklist

- [ ] App icon finalized (all sizes)
- [ ] Splash screen finalized
- [ ] All screenshots captured and formatted
- [ ] Feature graphic designed (Android)
- [ ] Privacy policy page live at URL
- [ ] Terms of service page live at URL
- [ ] Demo account created for Apple review
- [ ] Data safety questionnaire completed (Google Play)
- [ ] App privacy labels configured (Apple)
- [ ] Content rating questionnaire completed
- [ ] EAS project ID updated in app.json (replace "plateplanner" with actual UUID)
- [ ] Apple Developer account enrolled ($99/year)
- [ ] Google Play Developer account enrolled ($25 one-time)
- [ ] Google service account key generated for EAS Submit
- [ ] Apple App Store Connect app record created
- [ ] Google Play Console app record created
- [ ] Test on physical devices (iOS and Android)
- [ ] Run production build locally: `eas build --profile production --platform all`
- [ ] Submit to stores: `eas submit --profile production --platform all`
