/**
 * Nutrition Insights Screen
 * Visualizes Phase 4A backend endpoints:
 *   GET /nutrition/insights/recommendations
 *   GET /nutrition/insights/trends
 *   GET /nutrition/insights/goal-prediction
 *   GET /nutrition/insights/weekly-report
 */
import React, { useCallback, useState } from "react";
import {
    ScrollView,
    TouchableOpacity,
    ActivityIndicator,
    Dimensions,
    RefreshControl,
    View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Box, Text, VStack, HStack } from "@gluestack-ui/themed";
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";
import * as Haptics from "expo-haptics";
import Svg, {
    Rect,
    Path,
    Circle,
    Defs,
    LinearGradient as SvgGrad,
    Stop,
    Line,
    Text as SvgText,
} from "react-native-svg";
import { useAuth } from "../src/state/auth";
import { apiRequest } from "../src/api/client";
import { useFocusEffect } from "@react-navigation/native";

const SCREEN_W = Dimensions.get("window").width;
const CHART_W = SCREEN_W - 48;

// ─── Types ────────────────────────────────────────────────────────────────────
type Recommendation = {
    type: "alert" | "warning" | "info" | "success" | "tip";
    message: string;
    recipe_suggestions: string[];
};

type RecommendationsResponse = {
    period: string;
    total_recommendations: number;
    recommendations: Recommendation[];
};

type TrendsResponse = {
    analysis_period: string;
    calorie_trend: "increasing" | "decreasing" | "stable";
    protein_trend: "increasing" | "decreasing" | "stable";
    consistency_score: number;
    insights: string[];
    weeks_analyzed: number;
};

type GoalPrediction = {
    has_active_goal: boolean;
    goal_type?: string;
    prediction?: "highly_likely" | "likely" | "possible" | "unlikely";
    confidence?: number;
    message?: string;
    success_rate?: number;
    days_on_track?: number;
    days_off_track?: number;
    progress_pct?: number;
    days_remaining?: number;
    recommendations?: string[];
};

type WeeklyReport = {
    week?: string;
    summary?: string;
    highlights?: string[];
    areas_to_improve?: string[];
    wins?: string[];
    action_items?: string[];
};

// ─── Recommendation card ──────────────────────────────────────────────────────
const REC_STYLES: Record<
    string,
    { bg: string; border: string; icon: string; text: string }
> = {
    alert: { bg: "#fef2f2", border: "#fca5a5", icon: "🚨", text: "#b91c1c" },
    warning: { bg: "#fffbeb", border: "#fcd34d", icon: "⚠️", text: "#92400e" },
    info: { bg: "#eff6ff", border: "#93c5fd", icon: "ℹ️", text: "#1e40af" },
    success: { bg: "#f0fdf4", border: "#86efac", icon: "✅", text: "#166534" },
    tip: { bg: "#f5f3ff", border: "#c4b5fd", icon: "💡", text: "#5b21b6" },
};

function RecommendationCard({ rec }: { rec: Recommendation }) {
    const s = REC_STYLES[rec.type] ?? REC_STYLES.tip;
    return (
        <Box
            mb="$3"
            p="$4"
            borderRadius="$2xl"
            borderWidth={1}
            borderLeftWidth={4}
            style={{
                backgroundColor: s.bg,
                borderColor: s.border,
                borderLeftColor: s.border,
            }}
        >
            <HStack space="sm" alignItems="flex-start">
                <Text fontSize={18}>{s.icon}</Text>
                <VStack flex={1}>
                    <Text
                        size="sm"
                        style={{ color: s.text, fontWeight: "600", lineHeight: 20 }}
                    >
                        {rec.message}
                    </Text>
                    {rec.recipe_suggestions.length > 0 && (
                        <HStack flexWrap="wrap" mt="$2" style={{ gap: 6 }}>
                            {rec.recipe_suggestions.slice(0, 4).map((r, i) => (
                                <Box
                                    key={i}
                                    px="$2"
                                    py="$0.5"
                                    borderRadius="$full"
                                    style={{ backgroundColor: s.border + "60" }}
                                >
                                    <Text size="xs" style={{ color: s.text }}>
                                        {r.replace(/_/g, " ")}
                                    </Text>
                                </Box>
                            ))}
                        </HStack>
                    )}
                </VStack>
            </HStack>
        </Box>
    );
}

// ─── Consistency meter ────────────────────────────────────────────────────────
function ConsistencyMeter({ score }: { score: number }) {
    const pct = Math.min(score / 10, 1);
    const W = CHART_W;
    const H = 16;
    const fill = pct * W;
    const color =
        score >= 7 ? "#16a34a" : score >= 4 ? "#f59e0b" : "#ef4444";

    return (
        <Box>
            <HStack justifyContent="space-between" mb="$1">
                <Text size="xs" color="$coolGray500">Consistency Score</Text>
                <Text size="xs" bold style={{ color }}>
                    {score.toFixed(1)} / 10
                </Text>
            </HStack>
            <Svg width={W} height={H}>
                <Rect x={0} y={0} width={W} height={H} rx={H / 2} fill="#f3f4f6" />
                <Rect x={0} y={0} width={fill} height={H} rx={H / 2} fill={color} />
            </Svg>
        </Box>
    );
}

// ─── Trend pill ───────────────────────────────────────────────────────────────
function TrendPill({
    label,
    trend,
}: {
    label: string;
    trend: "increasing" | "decreasing" | "stable";
}) {
    const map = {
        increasing: { icon: "↑", color: "#16a34a", bg: "#dcfce7" },
        decreasing: { icon: "↓", color: "#dc2626", bg: "#fee2e2" },
        stable: { icon: "→", color: "#6b7280", bg: "#f3f4f6" },
    };
    const m = map[trend] ?? map.stable;
    return (
        <VStack alignItems="center" flex={1}>
            <Box
                px="$3"
                py="$1.5"
                borderRadius="$full"
                style={{ backgroundColor: m.bg }}
                mb="$1"
            >
                <Text bold style={{ color: m.color, fontSize: 18 }}>
                    {m.icon}
                </Text>
            </Box>
            <Text size="xs" color="$coolGray500">
                {label}
            </Text>
            <Text size="xs" bold style={{ color: m.color }}>
                {trend}
            </Text>
        </VStack>
    );
}

// ─── Goal prediction card ─────────────────────────────────────────────────────
function GoalPredictionCard({ pred }: { pred: GoalPrediction }) {
    if (!pred.has_active_goal) {
        return (
            <Box
                bg="$coolGray50"
                p="$4"
                borderRadius="$2xl"
                alignItems="center"
                borderWidth={1}
                borderColor="$coolGray200"
            >
                <Text fontSize={32} mb="$2">🎯</Text>
                <Text bold color="$coolGray700">No Active Goal</Text>
                <Text size="sm" color="$coolGray500" textAlign="center" mt="$1">
                    Set a nutrition goal to see your achievement prediction
                </Text>
            </Box>
        );
    }

    const confColor =
        (pred.confidence ?? 0) >= 80
            ? "#16a34a"
            : (pred.confidence ?? 0) >= 50
                ? "#f59e0b"
                : "#ef4444";

    const bgColors: Record<string, [string, string]> = {
        highly_likely: ["#16a34a", "#22c55e"],
        likely: ["#2563eb", "#3b82f6"],
        possible: ["#d97706", "#f59e0b"],
        unlikely: ["#dc2626", "#ef4444"],
    };
    const gradColors = bgColors[pred.prediction ?? "possible"] ?? bgColors.possible;

    // Confidence arc
    const R = 44;
    const CX = 56;
    const CY = 56;
    const conf = (pred.confidence ?? 0) / 100;
    const angle = conf * 2 * Math.PI;
    const x2 = CX + R * Math.sin(angle);
    const y2 = CY - R * Math.cos(angle);
    const largeArc = conf > 0.5 ? 1 : 0;
    const arcPath =
        conf >= 0.999
            ? `M ${CX} ${CY - R} A ${R} ${R} 0 1 1 ${CX - 0.01} ${CY - R}`
            : `M ${CX} ${CY - R} A ${R} ${R} 0 ${largeArc} 1 ${x2} ${y2}`;

    return (
        <Box>
            <LinearGradient
                colors={gradColors}
                style={{ borderRadius: 20, padding: 20, marginBottom: 12 }}
            >
                <HStack alignItems="center" justifyContent="space-between">
                    <VStack flex={1}>
                        <Text color="rgba(255,255,255,0.8)" size="xs" bold>
                            {(pred.goal_type ?? "").replace(/_/g, " ").toUpperCase()}
                        </Text>
                        <Text color="white" bold size="lg" mt="$1">
                            {pred.message ?? ""}
                        </Text>
                        <HStack space="md" mt="$3">
                            {[
                                { label: "On Track", value: `${pred.days_on_track ?? 0}d` },
                                { label: "Off Track", value: `${pred.days_off_track ?? 0}d` },
                                {
                                    label: "Progress",
                                    value: `${Math.round(pred.progress_pct ?? 0)}%`,
                                },
                            ].map((s) => (
                                <VStack key={s.label} alignItems="center">
                                    <Text color="white" bold size="xl">
                                        {s.value}
                                    </Text>
                                    <Text color="rgba(255,255,255,0.7)" size="xs">
                                        {s.label}
                                    </Text>
                                </VStack>
                            ))}
                        </HStack>
                    </VStack>
                    {/* Confidence Arc */}
                    <Svg width={112} height={112}>
                        <Circle
                            cx={CX}
                            cy={CY}
                            r={R}
                            stroke="rgba(255,255,255,0.2)"
                            strokeWidth={8}
                            fill="none"
                        />
                        <Path
                            d={arcPath}
                            fill="none"
                            stroke="white"
                            strokeWidth={8}
                            strokeLinecap="round"
                        />
                        <SvgText
                            x={CX}
                            y={CY - 6}
                            textAnchor="middle"
                            fontSize={18}
                            fontWeight="bold"
                            fill="white"
                        >
                            {pred.confidence}%
                        </SvgText>
                        <SvgText
                            x={CX}
                            y={CY + 10}
                            textAnchor="middle"
                            fontSize={10}
                            fill="rgba(255,255,255,0.7)"
                        >
                            confidence
                        </SvgText>
                    </Svg>
                </HStack>
            </LinearGradient>

            {/* Recommendations */}
            {(pred.recommendations ?? []).length > 0 && (
                <Box
                    bg="$white"
                    borderRadius="$2xl"
                    p="$4"
                    borderWidth={1}
                    borderColor="$coolGray100"
                >
                    <Text bold color="$coolGray800" mb="$3">
                        💡 How to Improve
                    </Text>
                    {pred.recommendations!.map((r, i) => (
                        <HStack key={i} space="sm" mb="$2" alignItems="flex-start">
                            <Text color="$green600">•</Text>
                            <Text size="sm" color="$coolGray600" flex={1}>
                                {r}
                            </Text>
                        </HStack>
                    ))}
                </Box>
            )}
        </Box>
    );
}

// ─── Weekly Report card ───────────────────────────────────────────────────────
function WeeklyReportCard({ report }: { report: WeeklyReport }) {
    const sections: { title: string; key: keyof WeeklyReport; emoji: string; color: string }[] = [
        { title: "Highlights", key: "highlights", emoji: "🌟", color: "#1e40af" },
        { title: "Wins", key: "wins", emoji: "🏆", color: "#166534" },
        { title: "Areas to Improve", key: "areas_to_improve", emoji: "📈", color: "#92400e" },
        { title: "Action Items", key: "action_items", emoji: "✅", color: "#5b21b6" },
    ];

    return (
        <Box bg="$white" borderRadius="$2xl" p="$4" borderWidth={1} borderColor="$coolGray100">
            {report.week && (
                <Text size="xs" color="$coolGray400" mb="$3">
                    📅 {report.week}
                </Text>
            )}
            {sections.map((s) => {
                const items = (report[s.key] as string[]) ?? [];
                if (!items.length) return null;
                return (
                    <Box key={s.key} mb="$4">
                        <Text bold color="$coolGray800" mb="$2">
                            {s.emoji} {s.title}
                        </Text>
                        {items.map((item, i) => (
                            <HStack key={i} space="sm" mb="$1.5" alignItems="flex-start">
                                <Box
                                    w={6}
                                    h={6}
                                    borderRadius="$full"
                                    mt="$1"
                                    style={{ backgroundColor: s.color + "60" }}
                                />
                                <Text size="sm" color="$coolGray600" flex={1}>
                                    {item}
                                </Text>
                            </HStack>
                        ))}
                    </Box>
                );
            })}
        </Box>
    );
}

// ─── Main Screen ──────────────────────────────────────────────────────────────
export default function InsightsScreen() {
    const { token } = useAuth();
    const router = useRouter();

    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [recommendations, setRecommendations] =
        useState<RecommendationsResponse | null>(null);
    const [trends, setTrends] = useState<TrendsResponse | null>(null);
    const [prediction, setPrediction] = useState<GoalPrediction | null>(null);
    const [weeklyReport, setWeeklyReport] = useState<WeeklyReport | null>(null);
    const [activeTab, setActiveTab] = useState<"recommendations" | "trends" | "prediction" | "report">(
        "recommendations"
    );

    const fetchAll = useCallback(async () => {
        if (!token) { setLoading(false); return; }
        try {
            const weekStart = new Date();
            weekStart.setDate(weekStart.getDate() - weekStart.getDay()); // Monday
            const weekStartStr = weekStart.toISOString().split("T")[0];

            const [rec, tr, pred, rep] = await Promise.allSettled([
                apiRequest<RecommendationsResponse>("/nutrition/insights/recommendations", { token }),
                apiRequest<TrendsResponse>("/nutrition/insights/trends?days=30", { token }),
                apiRequest<GoalPrediction>("/nutrition/insights/goal-prediction", { token }),
                apiRequest<WeeklyReport>(`/nutrition/insights/weekly-report?week_start=${weekStartStr}`, { token }),
            ]);

            if (rec.status === "fulfilled") setRecommendations(rec.value);
            if (tr.status === "fulfilled") setTrends(tr.value);
            if (pred.status === "fulfilled") setPrediction(pred.value);
            if (rep.status === "fulfilled") setWeeklyReport(rep.value);
        } catch (e) {
            console.log("Insights fetch error:", e);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [token]);

    useFocusEffect(useCallback(() => { fetchAll(); }, [fetchAll]));

    const onRefresh = () => { setRefreshing(true); fetchAll(); };

    const TABS = [
        { id: "recommendations" as const, label: "Tips", emoji: "💡" },
        { id: "trends" as const, label: "Trends", emoji: "📈" },
        { id: "prediction" as const, label: "Goal", emoji: "🎯" },
        { id: "report" as const, label: "Report", emoji: "📋" },
    ];

    const handleTabPress = (id: typeof activeTab) => {
        Haptics.selectionAsync();
        setActiveTab(id);
    };

    return (
        <SafeAreaView style={{ flex: 1, backgroundColor: "#FAFAFA" }} edges={["top", "left", "right"]}>
            {/* Header */}
            <Box px="$6" pt="$4" pb="$2" bg="$white" shadowColor="$black" shadowOffset={{ width: 0, height: 2 }} shadowOpacity={0.04} shadowRadius={4} elevation={2}>
                <HStack alignItems="center" justifyContent="space-between" mb="$4">
                    <TouchableOpacity onPress={() => { Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light); router.back(); }}>
                        <Text color="$green600" bold>‹ Back</Text>
                    </TouchableOpacity>
                    <VStack alignItems="center">
                        <Text size="xl" bold color="$coolGray900">Nutrition Insights</Text>
                        <Text size="xs" color="$coolGray400">AI-powered analysis</Text>
                    </VStack>
                    <Box w={50} />
                </HStack>

                {/* Tab bar */}
                <HStack space="sm" justifyContent="space-between">
                    {TABS.map((tab) => {
                        const active = activeTab === tab.id;
                        return (
                            <TouchableOpacity
                                key={tab.id}
                                onPress={() => handleTabPress(tab.id)}
                                style={{ flex: 1 }}
                                activeOpacity={0.7}
                            >
                                <Box
                                    py="$2"
                                    borderRadius="$xl"
                                    alignItems="center"
                                    style={{ backgroundColor: active ? "#16a34a" : "#f3f4f6" }}
                                >
                                    <Text fontSize={14}>{tab.emoji}</Text>
                                    <Text
                                        size="xs"
                                        bold
                                        style={{ color: active ? "white" : "#6b7280" }}
                                    >
                                        {tab.label}
                                    </Text>
                                </Box>
                            </TouchableOpacity>
                        );
                    })}
                </HStack>
            </Box>

            {loading ? (
                <Box flex={1} alignItems="center" justifyContent="center">
                    <ActivityIndicator size="large" color="#16a34a" />
                    <Text color="$coolGray500" mt="$4">Analysing your nutrition…</Text>
                </Box>
            ) : (
                <ScrollView
                    contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 120, paddingTop: 16 }}
                    showsVerticalScrollIndicator={false}
                    refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#16a34a" />}
                >
                    {/* ── RECOMMENDATIONS ─────────────────────────────────────────── */}
                    {activeTab === "recommendations" && (
                        <VStack>
                            {recommendations ? (
                                <>
                                    <HStack justifyContent="space-between" alignItems="center" mb="$4">
                                        <Text bold size="lg" color="$coolGray900">
                                            {recommendations.total_recommendations} Personalized Tips
                                        </Text>
                                        <Box px="$2" py="$0.5" bg="$green100" borderRadius="$full">
                                            <Text size="xs" color="$green700">{recommendations.period}</Text>
                                        </Box>
                                    </HStack>
                                    {recommendations.recommendations.map((rec, i) => (
                                        <RecommendationCard key={i} rec={rec} />
                                    ))}
                                </>
                            ) : (
                                <Box bg="$coolGray50" p="$6" borderRadius="$2xl" alignItems="center">
                                    <Text fontSize={40} mb="$2">💡</Text>
                                    <Text bold color="$coolGray700">No Recommendations Yet</Text>
                                    <Text size="sm" color="$coolGray500" textAlign="center" mt="$1">
                                        Log some meals to start getting personalised tips
                                    </Text>
                                </Box>
                            )}
                        </VStack>
                    )}

                    {/* ── TRENDS ──────────────────────────────────────────────────── */}
                    {activeTab === "trends" && trends && (
                        <VStack>
                            <Text bold size="lg" color="$coolGray900" mb="$4">
                                30-Day Nutrition Trends
                            </Text>

                            {/* Trend pills */}
                            <Box bg="$white" borderRadius="$2xl" p="$4" borderWidth={1} borderColor="$coolGray100" mb="$4">
                                <HStack justifyContent="space-between">
                                    <TrendPill label="Calories" trend={trends.calorie_trend} />
                                    <TrendPill label="Protein" trend={trends.protein_trend} />
                                </HStack>
                            </Box>

                            {/* Consistency */}
                            <Box bg="$white" borderRadius="$2xl" p="$4" borderWidth={1} borderColor="$coolGray100" mb="$4">
                                <ConsistencyMeter score={trends.consistency_score} />
                            </Box>

                            {/* Insights */}
                            <Box bg="$white" borderRadius="$2xl" p="$4" borderWidth={1} borderColor="$coolGray100">
                                <Text bold color="$coolGray800" mb="$3">📊 Key Insights</Text>
                                {trends.insights.map((insight, i) => (
                                    <HStack key={i} space="sm" mb="$2" alignItems="flex-start">
                                        <Text color="$green600" bold>•</Text>
                                        <Text size="sm" color="$coolGray600" flex={1}>{insight}</Text>
                                    </HStack>
                                ))}
                            </Box>
                        </VStack>
                    )}
                    {activeTab === "trends" && !trends && (
                        <Box bg="$coolGray50" p="$6" borderRadius="$2xl" alignItems="center">
                            <Text fontSize={40} mb="$2">📈</Text>
                            <Text bold color="$coolGray700">No Trend Data</Text>
                            <Text size="sm" color="$coolGray500" textAlign="center" mt="$1">
                                Log meals consistently for trend analysis
                            </Text>
                        </Box>
                    )}

                    {/* ── GOAL PREDICTION ─────────────────────────────────────────── */}
                    {activeTab === "prediction" && (
                        <VStack>
                            <Text bold size="lg" color="$coolGray900" mb="$4">
                                Goal Achievement Prediction
                            </Text>
                            {prediction ? (
                                <GoalPredictionCard pred={prediction} />
                            ) : (
                                <Box bg="$coolGray50" p="$6" borderRadius="$2xl" alignItems="center">
                                    <Text fontSize={40} mb="$2">🎯</Text>
                                    <Text bold color="$coolGray700">No Goal Data</Text>
                                </Box>
                            )}
                        </VStack>
                    )}

                    {/* ── WEEKLY REPORT ────────────────────────────────────────────── */}
                    {activeTab === "report" && (
                        <VStack>
                            <Text bold size="lg" color="$coolGray900" mb="$4">
                                Weekly Report
                            </Text>
                            {weeklyReport ? (
                                <WeeklyReportCard report={weeklyReport} />
                            ) : (
                                <Box bg="$coolGray50" p="$6" borderRadius="$2xl" alignItems="center">
                                    <Text fontSize={40} mb="$2">📋</Text>
                                    <Text bold color="$coolGray700">No Report This Week</Text>
                                    <Text size="sm" color="$coolGray500" textAlign="center" mt="$1">
                                        Log meals this week to generate your report
                                    </Text>
                                </Box>
                            )}
                        </VStack>
                    )}
                </ScrollView>
            )}
        </SafeAreaView>
    );
}
