import React from "react";
import { View, Text, Image } from "react-native";
import { Clock, Flame, Heart } from "lucide-react-native";

interface RecipeCardProps {
  title: string;
  calories: number;
  time: string;
  imageColor: string; // Using color blocks for now, can be images later
  tags: string[];
}

export function RecipeCard({ title, calories, time, imageColor, tags }: RecipeCardProps) {
  return (
    <View className="bg-white rounded-3xl p-3 mb-6 shadow-sm border border-gray-100">
      {/* Image Placeholder */}
      <View className={`h-40 w-full rounded-2xl mb-3 relative items-center justify-center`} style={{ backgroundColor: imageColor }}>
        <Text className="text-white opacity-50 font-bold text-lg">Food Image</Text>
        <View className="absolute top-3 right-3 bg-white/20 p-2 rounded-full backdrop-blur-md">
            <Heart size={20} color="white" fill="white" />
        </View>
      </View>

      <View className="px-2 pb-2">
        <Text className="text-xl font-bold text-gray-900 mb-1">{title}</Text>
        
        {/* Tags Row */}
        <View className="flex-row gap-2 mb-3">
            {tags.map((tag, i) => (
                <View key={i} className="bg-gray-100 px-2 py-1 rounded-md">
                    <Text className="text-xs text-gray-500 font-medium">{tag}</Text>
                </View>
            ))}
        </View>

        {/* Metadata Row */}
        <View className="flex-row justify-between items-center mt-1">
            <View className="flex-row gap-4">
                <View className="flex-row items-center gap-1">
                    <Flame size={16} color="#FF6B4A" />
                    <Text className="text-gray-500 font-medium">{calories} kcal</Text>
                </View>
                <View className="flex-row items-center gap-1">
                    <Clock size={16} color="#9CA3AF" />
                    <Text className="text-gray-500 font-medium">{time}</Text>
                </View>
            </View>
            
            <View className="bg-primary px-4 py-2 rounded-full">
                <Text className="text-white font-bold text-sm">View</Text>
            </View>
        </View>
      </View>
    </View>
  );
}
