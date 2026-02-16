import React from "react";
import { View, Dimensions } from "react-native";
import Svg, { Path, Defs, LinearGradient, Stop } from "react-native-svg";

export function DietGraph() {
  const width = Dimensions.get("window").width - 48; // Padding
  const height = 150;

  // A smooth curve path resembling the design
  const pathData = `
    M 0,${height} 
    L 0,100 
    C 40,100 60,130 100,120 
    C 140,110 160,80 200,90 
    C 240,100 280,110 320,60 
    L 320,${height} 
    Z
  `;

  // The line on top
  const linePath = `
    M 0,100 
    C 40,100 60,130 100,120 
    C 140,110 160,80 200,90 
    C 240,100 280,110 320,60
  `;

  return (
    <View className="mt-6">
      <Svg width={width} height={height}>
        <Defs>
          <LinearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#4ade80" stopOpacity="0.4" />
            <Stop offset="1" stopColor="#4ade80" stopOpacity="0" />
          </LinearGradient>
        </Defs>

        {/* Fill Area */}
        <Path d={pathData} fill="url(#grad)" />

        {/* Stroke Line */}
        <Path d={linePath} fill="none" stroke="#4ade80" strokeWidth="3" />

        {/* Data Point Tooltip (Mock) */}
        <View className="absolute left-40 top-10 bg-primary px-3 py-1 rounded-lg shadow-lg" style={{ left: 180, top: 40 }}>
          {/* This would be positioned absolutely in a real implementation */}
        </View>
      </Svg>
    </View>
  );
}
