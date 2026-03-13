import React from "react";
import { View, Dimensions } from "react-native";
import Svg, { Rect, Path, Defs, LinearGradient, Stop, Text as SvgText } from "react-native-svg";

type DayData = {
  day: string;
  calories: number;
};

type Props = {
  data?: DayData[];
  target?: number;
};

export function DietGraph({ data, target = 2000 }: Props) {
  const width = Dimensions.get("window").width - 48;
  const height = 150;
  const barWidth = 28;
  const padding = { top: 10, bottom: 25, left: 8, right: 8 };
  const chartHeight = height - padding.top - padding.bottom;

  // If no data, show placeholder
  if (!data || data.length === 0) {
    const placeholderPath = `
      M 0,${height}
      L 0,100
      C 40,100 60,130 100,120
      C 140,110 160,80 200,90
      C 240,100 280,110 320,60
      L 320,${height}
      Z
    `;
    const placeholderLine = `
      M 0,100
      C 40,100 60,130 100,120
      C 140,110 160,80 200,90
      C 240,100 280,110 320,60
    `;
    return (
      <View style={{ marginTop: 6 }}>
        <Svg width={width} height={height}>
          <Defs>
            <LinearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
              <Stop offset="0" stopColor="#4ade80" stopOpacity="0.4" />
              <Stop offset="1" stopColor="#4ade80" stopOpacity="0" />
            </LinearGradient>
          </Defs>
          <Path d={placeholderPath} fill="url(#grad)" />
          <Path d={placeholderLine} fill="none" stroke="#4ade80" strokeWidth="3" />
        </Svg>
      </View>
    );
  }

  const maxCalories = Math.max(target, ...data.map((d) => d.calories), 1);
  const gap = (width - padding.left - padding.right - data.length * barWidth) / Math.max(data.length - 1, 1);

  return (
    <View style={{ marginTop: 6 }}>
      <Svg width={width} height={height}>
        <Defs>
          <LinearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#22c55e" stopOpacity="1" />
            <Stop offset="1" stopColor="#4ade80" stopOpacity="0.6" />
          </LinearGradient>
        </Defs>

        {data.map((d, i) => {
          const barHeight = Math.max((d.calories / maxCalories) * chartHeight, 4);
          const x = padding.left + i * (barWidth + gap);
          const y = padding.top + chartHeight - barHeight;
          const isOverTarget = d.calories > target;

          return (
            <React.Fragment key={i}>
              <Rect
                x={x}
                y={y}
                width={barWidth}
                height={barHeight}
                rx={6}
                ry={6}
                fill={isOverTarget ? "#f87171" : "url(#barGrad)"}
              />
              <SvgText
                x={x + barWidth / 2}
                y={height - 4}
                fontSize={10}
                fill="#9ca3af"
                textAnchor="middle"
              >
                {d.day}
              </SvgText>
              {d.calories > 0 && (
                <SvgText
                  x={x + barWidth / 2}
                  y={y - 4}
                  fontSize={9}
                  fill="#374151"
                  textAnchor="middle"
                  fontWeight="bold"
                >
                  {d.calories}
                </SvgText>
              )}
            </React.Fragment>
          );
        })}
      </Svg>
    </View>
  );
}
