import React from "react";
import { View, Text } from "react-native";
import Svg, { Path, Circle } from "react-native-svg";
import Animated, { useAnimatedProps, withTiming, useSharedValue, withDelay } from "react-native-reanimated";

// Simplified component without complex Animated.createAnimatedComponent for now
// to ensure stability on first load.

interface NutritionArcProps {
  calories: number;
  target: number;
}

export function NutritionArc({ calories, target }: NutritionArcProps) {
  const radius = 120;
  const strokeWidth = 20;
  const center = radius + strokeWidth;

  // Simple calculation for a progress arc
  const percentage = Math.min(calories / target, 1);
  const circumference = Math.PI * radius; // Half circle circumference
  const strokeDashoffset = circumference * (1 - percentage);

  return (
    <View className="items-center justify-center mt-4">
      <Svg width={center * 2} height={center + 20} viewBox={`0 0 ${center * 2} ${center + 40}`}>
        {/* Background Arc (Gray) */}
        <Path
          d={`M ${strokeWidth},${center} A ${radius},${radius} 0 0,1 ${center * 2 - strokeWidth},${center}`}
          fill="none"
          stroke="#F3F4F6"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />

        {/* Progress Arc (Green) */}
        <Path
          d={`M ${strokeWidth},${center} A ${radius},${radius} 0 0,1 ${center * 2 - strokeWidth},${center}`}
          fill="none"
          stroke="#4ade80" // Avocado Green
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset={strokeDashoffset}
        />
      </Svg>

      {/* Central Text */}
      <View className="absolute top-24 items-center" style={{ left: 0, right: 0 }}>
        {/* Removed Fire Emoji */}
        <Text className="text-4xl font-bold text-gray-800">{calories}</Text>
        <Text className="text-gray-400 text-sm font-medium">of {target} kcal</Text>
      </View>
    </View>
  );
}
