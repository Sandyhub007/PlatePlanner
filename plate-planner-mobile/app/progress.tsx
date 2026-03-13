import { ScrollView, ActivityIndicator, TouchableOpacity, Dimensions } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Box, Text, VStack, HStack } from "@gluestack-ui/themed";
import { useState, useEffect, useCallback } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { useRouter } from "expo-router";
import * as Haptics from "expo-haptics";
import Svg, {
  Rect,
  Path,
  Circle,
  Line,
  Text as SvgText,
  Defs,
  LinearGradient as SvgLinearGradient,
  Stop,
} from "react-native-svg";
import { useAuth } from "../src/state/auth";
import { apiRequest } from "../src/api/client";

const SCREEN_W = Dimensions.get("window").width;
const CHART_W = SCREEN_W - 48;

type DayData = {
  date: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  meals_count: number;
  on_track: boolean | null;
};

type RangeResponse = {
  start: string;
  end: string;
  daily_calorie_target: number | null;
  days: DayData[];
};

function formatShortDate(dateStr: string): string {
  const d = new Date(dateStr + "T12:00:00");
  return d.toLocaleDateString("en-US", { weekday: "short" }).slice(0, 3);
}

function formatMonthDay(dateStr: string): string {
  const d = new Date(dateStr + "T12:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

// ===================== BAR CHART =====================
function WeeklyCaloriesChart({ days, target }: { days: DayData[]; target: number }) {
  const h = 160;
  const barW = 28;
  const gap = (CHART_W - days.length * barW) / (days.length + 1);
  const maxCal = Math.max(...days.map(d => d.calories), target, 100);

  return (
    <Box bg="$white" borderRadius="$2xl" p="$4" mb="$4" borderWidth={1} borderColor="$coolGray100">
      <Text bold color="$coolGray800" mb="$3">Weekly Calories</Text>
      <Svg width={CHART_W} height={h + 30}>
        <Defs>
          <SvgLinearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#16a34a" stopOpacity="1" />
            <Stop offset="1" stopColor="#22c55e" stopOpacity="0.6" />
          </SvgLinearGradient>
          <SvgLinearGradient id="overGrad" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#f97316" stopOpacity="1" />
            <Stop offset="1" stopColor="#fb923c" stopOpacity="0.6" />
          </SvgLinearGradient>
        </Defs>

        {/* Target line */}
        {target > 0 && (
          <Line
            x1={0}
            y1={h - (target / maxCal) * h}
            x2={CHART_W}
            y2={h - (target / maxCal) * h}
            stroke="#e5e7eb"
            strokeWidth={1.5}
            strokeDasharray="6,4"
          />
        )}

        {days.map((d, i) => {
          const x = gap + i * (barW + gap);
          const barH = Math.max((d.calories / maxCal) * h, d.calories > 0 ? 4 : 0);
          const y = h - barH;
          const over = target > 0 && d.calories > target + 200;
          const empty = d.calories === 0;

          return (
            <React.Fragment key={d.date}>
              <Rect
                x={x}
                y={empty ? h - 4 : y}
                width={barW}
                height={empty ? 4 : barH}
                rx={6}
                fill={empty ? "#f3f4f6" : over ? "url(#overGrad)" : "url(#barGrad)"}
              />
              <SvgText
                x={x + barW / 2}
                y={h + 18}
                textAnchor="middle"
                fontSize={10}
                fill="#9ca3af"
              >
                {formatShortDate(d.date)}
              </SvgText>
              {d.calories > 0 && (
                <SvgText
                  x={x + barW / 2}
                  y={y - 4}
                  textAnchor="middle"
                  fontSize={9}
                  fill={over ? "#f97316" : "#16a34a"}
                >
                  {d.calories}
                </SvgText>
              )}
            </React.Fragment>
          );
        })}
      </Svg>

      {/* Legend */}
      <HStack space="md" mt="$1">
        <HStack space="xs" alignItems="center">
          <Box w={10} h={10} bg="$green500" borderRadius="$sm" />
          <Text size="xs" color="$coolGray500">On track</Text>
        </HStack>
        <HStack space="xs" alignItems="center">
          <Box w={10} h={10} bg="$orange400" borderRadius="$sm" />
          <Text size="xs" color="$coolGray500">Over goal</Text>
        </HStack>
        {target > 0 && (
          <HStack space="xs" alignItems="center">
            <Box w={16} h={2} bg="$coolGray300" />
            <Text size="xs" color="$coolGray500">Target ({target} kcal)</Text>
          </HStack>
        )}
      </HStack>
    </Box>
  );
}

// ===================== DONUT CHART =====================
function MacroDonutChart({ days }: { days: DayData[] }) {
  const totalProtein = days.reduce((s, d) => s + (d.protein_g || 0), 0);
  const totalCarbs = days.reduce((s, d) => s + (d.carbs_g || 0), 0);
  const totalFat = days.reduce((s, d) => s + (d.fat_g || 0), 0);

  const totalCal = totalProtein * 4 + totalCarbs * 4 + totalFat * 9;

  const proteinPct = totalCal > 0 ? totalProtein * 4 / totalCal : 0.33;
  const carbsPct = totalCal > 0 ? totalCarbs * 4 / totalCal : 0.34;
  const fatPct = totalCal > 0 ? totalFat * 9 / totalCal : 0.33;

  const R = 55;
  const CX = 70;
  const CY = 70;

  function arcPath(startPct: number, endPct: number): string {
    const start = startPct * 2 * Math.PI - Math.PI / 2;
    const end = endPct * 2 * Math.PI - Math.PI / 2;
    const x1 = CX + R * Math.cos(start);
    const y1 = CY + R * Math.sin(start);
    const x2 = CX + R * Math.cos(end);
    const y2 = CY + R * Math.sin(end);
    const largeArc = endPct - startPct > 0.5 ? 1 : 0;
    return `M ${CX} ${CY} L ${x1} ${y1} A ${R} ${R} 0 ${largeArc} 1 ${x2} ${y2} Z`;
  }

  const segments = [
    { pct: proteinPct, color: "#3b82f6", label: "Protein", grams: Math.round(totalProtein) },
    { pct: carbsPct, color: "#f59e0b", label: "Carbs", grams: Math.round(totalCarbs) },
    { pct: fatPct, color: "#ef4444", label: "Fat", grams: Math.round(totalFat) },
  ];

  let cumulative = 0;

  return (
    <Box bg="$white" borderRadius="$2xl" p="$4" mb="$4" borderWidth={1} borderColor="$coolGray100">
      <Text bold color="$coolGray800" mb="$3">Macro Breakdown (This Week)</Text>
      {totalCal === 0 ? (
        <Box py="$6" alignItems="center">
          <Text color="$coolGray400">No meals logged this week yet</Text>
        </Box>
      ) : (
        <HStack alignItems="center" space="xl">
          <Svg width={140} height={140}>
            {segments.map((seg, i) => {
              const start = cumulative;
              cumulative += seg.pct;
              return (
                <Path key={i} d={arcPath(start, cumulative)} fill={seg.color} opacity={0.9} />
              );
            })}
            {/* Center hole */}
            <Circle cx={CX} cy={CY} r={30} fill="white" />
            <SvgText x={CX} y={CY - 6} textAnchor="middle" fontSize={11} fill="#374151" fontWeight="bold">
              {Math.round(totalCal / (days.filter(d => d.calories > 0).length || 1))}
            </SvgText>
            <SvgText x={CX} y={CY + 8} textAnchor="middle" fontSize={9} fill="#9ca3af">
              kcal/day
            </SvgText>
          </Svg>

          <VStack space="sm" flex={1}>
            {segments.map(seg => (
              <HStack key={seg.label} alignItems="center" space="sm">
                <Box w={10} h={10} borderRadius="$sm" style={{ backgroundColor: seg.color }} />
                <VStack>
                  <Text size="xs" color="$coolGray500">{seg.label}</Text>
                  <Text size="sm" bold color="$coolGray800">{seg.grams}g · {Math.round(seg.pct * 100)}%</Text>
                </VStack>
              </HStack>
            ))}
          </VStack>
        </HStack>
      )}
    </Box>
  );
}

// ===================== TREND LINE CHART =====================
function TrendLineChart({ days, target }: { days: DayData[]; target: number }) {
  const h = 140;
  const pad = { left: 36, right: 8, top: 10, bottom: 24 };
  const chartW = CHART_W - pad.left - pad.right;
  const chartH = h - pad.top - pad.bottom;

  const filledDays = days.filter(d => d.calories > 0);
  if (filledDays.length < 2) {
    return (
      <Box bg="$white" borderRadius="$2xl" p="$4" mb="$4" borderWidth={1} borderColor="$coolGray100">
        <Text bold color="$coolGray800" mb="$3">30-Day Calorie Trend</Text>
        <Box py="$6" alignItems="center">
          <Text color="$coolGray400">Log meals for 2+ days to see your trend</Text>
        </Box>
      </Box>
    );
  }

  const maxCal = Math.max(...days.map(d => d.calories), target || 0, 100);
  const minCal = 0;
  const range = maxCal - minCal || 1;

  const toX = (i: number) => pad.left + (i / (days.length - 1)) * chartW;
  const toY = (cal: number) => pad.top + chartH - ((cal - minCal) / range) * chartH;

  // Build the line path (only through non-zero points)
  const points = days
    .map((d, i) => ({ x: toX(i), y: toY(d.calories), cal: d.calories, date: d.date }))
    .filter(p => p.cal > 0);

  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");

  // Area fill
  const areaPath = linePath + ` L ${points[points.length - 1].x} ${pad.top + chartH} L ${points[0].x} ${pad.top + chartH} Z`;

  // Target line y
  const targetY = target > 0 ? toY(target) : null;

  // Y axis labels
  const yLabels = [0, Math.round(maxCal / 2), maxCal];

  // X axis: show every ~7th date label
  const step = Math.max(1, Math.floor(days.length / 5));

  return (
    <Box bg="$white" borderRadius="$2xl" p="$4" mb="$4" borderWidth={1} borderColor="$coolGray100">
      <Text bold color="$coolGray800" mb="$3">30-Day Calorie Trend</Text>
      <Svg width={CHART_W} height={h}>
        <Defs>
          <SvgLinearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#16a34a" stopOpacity="0.25" />
            <Stop offset="1" stopColor="#16a34a" stopOpacity="0" />
          </SvgLinearGradient>
        </Defs>

        {/* Y axis labels */}
        {yLabels.map((v, i) => (
          <SvgText key={i} x={pad.left - 4} y={toY(v) + 4} textAnchor="end" fontSize={9} fill="#9ca3af">
            {v > 0 ? `${v}` : "0"}
          </SvgText>
        ))}

        {/* Target line */}
        {targetY !== null && (
          <Line
            x1={pad.left}
            y1={targetY}
            x2={pad.left + chartW}
            y2={targetY}
            stroke="#22c55e"
            strokeWidth={1}
            strokeDasharray="6,3"
            opacity={0.6}
          />
        )}

        {/* Area fill */}
        <Path d={areaPath} fill="url(#trendGrad)" />

        {/* Line */}
        <Path d={linePath} fill="none" stroke="#16a34a" strokeWidth={2.5} strokeLinejoin="round" />

        {/* Dots */}
        {points.map((p, i) => {
          const onTrack = target > 0 && Math.abs(p.cal - target) <= 200;
          return (
            <Circle
              key={i}
              cx={p.x}
              cy={p.y}
              r={4}
              fill={onTrack ? "#16a34a" : "#f97316"}
              stroke="white"
              strokeWidth={1.5}
            />
          );
        })}

        {/* X axis labels (sparse) */}
        {days.map((d, i) => {
          if (i % step !== 0 && i !== days.length - 1) return null;
          return (
            <SvgText key={d.date} x={toX(i)} y={h - 4} textAnchor="middle" fontSize={8} fill="#9ca3af">
              {formatMonthDay(d.date)}
            </SvgText>
          );
        })}
      </Svg>

      <HStack space="md" mt="$1">
        <HStack space="xs" alignItems="center">
          <Circle cx={5} cy={5} r={5} fill="#16a34a" />
          <Box w={10} h={10} borderRadius="$full" bg="$green600" />
          <Text size="xs" color="$coolGray500">On track</Text>
        </HStack>
        <HStack space="xs" alignItems="center">
          <Box w={10} h={10} borderRadius="$full" bg="$orange400" />
          <Text size="xs" color="$coolGray500">Over goal</Text>
        </HStack>
      </HStack>
    </Box>
  );
}

// ===================== MAIN SCREEN =====================
export default function ProgressScreen() {
  const router = useRouter();
  const { token } = useAuth();

  const [loading, setLoading] = useState(false);
  const [weekData, setWeekData] = useState<DayData[]>([]);
  const [monthData, setMonthData] = useState<DayData[]>([]);
  const [target, setTarget] = useState(0);

  const fetchData = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const today = new Date();
      const todayStr = today.toISOString().split("T")[0];

      // Last 7 days
      const weekStart = new Date(today);
      weekStart.setDate(today.getDate() - 6);
      const weekStartStr = weekStart.toISOString().split("T")[0];

      // Last 30 days
      const monthStart = new Date(today);
      monthStart.setDate(today.getDate() - 29);
      const monthStartStr = monthStart.toISOString().split("T")[0];

      const [weekResp, monthResp] = await Promise.all([
        apiRequest<RangeResponse>(`/nutrition/log/range?start=${weekStartStr}&end=${todayStr}`, { token }),
        apiRequest<RangeResponse>(`/nutrition/log/range?start=${monthStartStr}&end=${todayStr}`, { token }),
      ]);

      // Build full 7-day array (fill missing days with 0)
      const weekMap: Record<string, DayData> = {};
      for (const d of weekResp.days) weekMap[d.date] = d;
      const weekFull: DayData[] = [];
      for (let i = 0; i < 7; i++) {
        const d = new Date(weekStart);
        d.setDate(weekStart.getDate() + i);
        const s = d.toISOString().split("T")[0];
        weekFull.push(weekMap[s] ?? { date: s, calories: 0, protein_g: 0, carbs_g: 0, fat_g: 0, meals_count: 0, on_track: null });
      }
      setWeekData(weekFull);

      // 30-day array
      const monthMap: Record<string, DayData> = {};
      for (const d of monthResp.days) monthMap[d.date] = d;
      const monthFull: DayData[] = [];
      for (let i = 0; i < 30; i++) {
        const d = new Date(monthStart);
        d.setDate(monthStart.getDate() + i);
        const s = d.toISOString().split("T")[0];
        monthFull.push(monthMap[s] ?? { date: s, calories: 0, protein_g: 0, carbs_g: 0, fat_g: 0, meals_count: 0, on_track: null });
      }
      setMonthData(monthFull);

      setTarget(weekResp.daily_calorie_target || monthResp.daily_calorie_target || 0);
    } catch (e: any) {
      console.log("Progress fetch error:", e?.message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useFocusEffect(useCallback(() => { fetchData(); }, [fetchData]));

  // Stats summary
  const daysLogged = weekData.filter(d => d.calories > 0).length;
  const avgCals = daysLogged > 0
    ? Math.round(weekData.reduce((s, d) => s + d.calories, 0) / daysLogged)
    : 0;
  const daysOnTrack = weekData.filter(d => d.on_track === true).length;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#FAFAFA" }} edges={["top", "left", "right"]}>
      {/* Header */}
      <Box px="$6" pt="$4" pb="$4" bg="$white" shadowColor="$black" shadowOffset={{ width: 0, height: 2 }} shadowOpacity={0.04} shadowRadius={4} elevation={2}>
        <HStack alignItems="center" justifyContent="space-between">
          <TouchableOpacity onPress={() => { Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light); router.back(); }}>
            <Text color="$green600" bold>‹ Back</Text>
          </TouchableOpacity>
          <Text size="xl" bold color="$coolGray900">Progress</Text>
          <Box w={50} />
        </HStack>
      </Box>

      {loading ? (
        <Box flex={1} alignItems="center" justifyContent="center">
          <ActivityIndicator size="large" color="#16a34a" />
          <Text color="$coolGray500" mt="$4">Loading your progress...</Text>
        </Box>
      ) : (
        <ScrollView contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 40 }}>

          {/* Weekly Stats Row */}
          <HStack space="sm" mt="$4" mb="$4">
            {[
              { label: "Days Logged", value: `${daysLogged}/7`, color: "$green600" },
              { label: "Avg Calories", value: avgCals > 0 ? `${avgCals}` : "—", color: "$blue600" },
              { label: "On Target", value: `${daysOnTrack}d`, color: daysOnTrack >= 4 ? "$green600" : "$orange500" },
            ].map(stat => (
              <Box key={stat.label} flex={1} bg="$white" borderRadius="$xl" p="$3" alignItems="center" borderWidth={1} borderColor="$coolGray100">
                <Text bold size="xl" color={stat.color}>{stat.value}</Text>
                <Text size="xs" color="$coolGray500" textAlign="center">{stat.label}</Text>
              </Box>
            ))}
          </HStack>

          {/* Charts */}
          <WeeklyCaloriesChart days={weekData} target={target} />
          <MacroDonutChart days={weekData} />
          <TrendLineChart days={monthData} target={target} />

          {/* Empty state CTA */}
          {daysLogged === 0 && (
            <Box bg="$green50" borderRadius="$2xl" p="$5" alignItems="center" mb="$4" borderWidth={1} borderColor="$green200">
              <Text size="3xl" mb="$2">📊</Text>
              <Text bold color="$green800" mb="$1">No data yet</Text>
              <Text color="$green700" textAlign="center" size="sm">
                Start logging meals to see your progress charts here.
              </Text>
              <TouchableOpacity onPress={() => router.push('/meal-log')} style={{ marginTop: 12 }}>
                <Box bg="$green600" px="$5" py="$3" borderRadius="$full">
                  <Text color="$white" bold>Log a Meal →</Text>
                </Box>
              </TouchableOpacity>
            </Box>
          )}

        </ScrollView>
      )}
    </SafeAreaView>
  );
}

// Need React import for Fragment in the bar chart
import React from "react";
