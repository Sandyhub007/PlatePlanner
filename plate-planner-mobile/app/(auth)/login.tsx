import React, { useState, useRef, useEffect } from "react";
import {
    ScrollView,
    KeyboardAvoidingView,
    Platform,
    Animated,
    Pressable,
    ActivityIndicator,
    Alert,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import {
    Box,
    Text,
    VStack,
    HStack,
    Input,
    InputField,
    InputSlot,
} from "@gluestack-ui/themed";
import { Mail, Lock, Eye, EyeOff } from "lucide-react-native";
import { useAuth } from "../../src/state/auth";

export default function LoginScreen() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [errors, setErrors] = useState<{ email?: string; password?: string }>(
        {}
    );

    const router = useRouter();
    const { login, loginWithGoogle } = useAuth();

    // Animations
    const logoScale = useRef(new Animated.Value(0)).current;
    const formOpacity = useRef(new Animated.Value(0)).current;
    const formTranslateY = useRef(new Animated.Value(30)).current;
    const buttonScale = useRef(new Animated.Value(1)).current;

    useEffect(() => {
        Animated.sequence([
            Animated.spring(logoScale, {
                toValue: 1,
                tension: 50,
                friction: 7,
                useNativeDriver: true,
            }),
            Animated.parallel([
                Animated.timing(formOpacity, {
                    toValue: 1,
                    duration: 500,
                    useNativeDriver: true,
                }),
                Animated.timing(formTranslateY, {
                    toValue: 0,
                    duration: 500,
                    useNativeDriver: true,
                }),
            ]),
        ]).start();
    }, []);

    const validate = () => {
        const newErrors: { email?: string; password?: string } = {};
        if (!email.trim()) {
            newErrors.email = "Email is required";
        } else if (!/\S+@\S+\.\S+/.test(email)) {
            newErrors.email = "Enter a valid email";
        }
        if (!password) {
            newErrors.password = "Password is required";
        }
        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleLogin = async () => {
        if (!validate()) return;
        setIsLoading(true);
        try {
            await login(email.trim(), password);
            // AuthGate handles redirect
        } catch (e: any) {
            Alert.alert(
                "Login Failed",
                e?.message?.includes("401")
                    ? "Incorrect email or password. Please try again."
                    : "Something went wrong. Please check your connection and try again."
            );
        } finally {
            setIsLoading(false);
        }
    };

    const handleGoogleSignIn = async () => {
        await loginWithGoogle();
    };

    const onPressIn = () => {
        Animated.spring(buttonScale, {
            toValue: 0.96,
            useNativeDriver: true,
        }).start();
    };

    const onPressOut = () => {
        Animated.spring(buttonScale, {
            toValue: 1,
            useNativeDriver: true,
        }).start();
    };

    return (
        <SafeAreaView style={{ flex: 1, backgroundColor: "#FAFAFA" }}>
            <KeyboardAvoidingView
                style={{ flex: 1 }}
                behavior={Platform.OS === "ios" ? "padding" : "height"}
            >
                <ScrollView
                    contentContainerStyle={{
                        flexGrow: 1,
                        justifyContent: "center",
                        paddingHorizontal: 24,
                    }}
                    keyboardShouldPersistTaps="handled"
                    showsVerticalScrollIndicator={false}
                >
                    {/* Logo & Branding */}
                    <Animated.View
                        style={{
                            transform: [{ scale: logoScale }],
                            alignItems: "center",
                            marginBottom: 40,
                        }}
                    >
                        <Box
                            w={80}
                            h={80}
                            borderRadius={40}
                            alignItems="center"
                            justifyContent="center"
                            style={{
                                backgroundColor: "#16a34a",
                                shadowColor: "#16a34a",
                                shadowOffset: { width: 0, height: 8 },
                                shadowOpacity: 0.35,
                                shadowRadius: 16,
                                elevation: 12,
                            }}
                        >
                            <Text fontSize={36}>🍽️</Text>
                        </Box>
                        <Text
                            mt="$3"
                            fontSize={28}
                            fontWeight="$bold"
                            color="$coolGray900"
                            letterSpacing={-0.5}
                        >
                            PlatePlanner
                        </Text>
                        <Text mt="$1" fontSize={15} color="$coolGray400">
                            Plan smarter, eat better
                        </Text>
                    </Animated.View>

                    {/* Form */}
                    <Animated.View
                        style={{
                            opacity: formOpacity,
                            transform: [{ translateY: formTranslateY }],
                        }}
                    >
                        <Box
                            bg="$white"
                            borderRadius={24}
                            p="$6"
                            style={{
                                shadowColor: "#000",
                                shadowOffset: { width: 0, height: 4 },
                                shadowOpacity: 0.06,
                                shadowRadius: 16,
                                elevation: 4,
                            }}
                        >
                            <Text
                                fontSize={22}
                                fontWeight="$bold"
                                color="$coolGray900"
                                mb="$1"
                            >
                                Welcome back
                            </Text>
                            <Text fontSize={14} color="$coolGray400" mb="$6">
                                Sign in to continue your journey
                            </Text>

                            {/* Email */}
                            <VStack space="xs" mb="$4">
                                <Text fontSize={13} fontWeight="$medium" color="$coolGray600">
                                    Email
                                </Text>
                                <Input
                                    variant="outline"
                                    size="xl"
                                    borderRadius={14}
                                    borderColor={errors.email ? "$red400" : "$coolGray200"}
                                    bg="$coolGray50"
                                >
                                    <InputSlot pl="$3">
                                        <Mail
                                            size={18}
                                            color={errors.email ? "#F87171" : "#9CA3AF"}
                                        />
                                    </InputSlot>
                                    <InputField
                                        placeholder="your@email.com"
                                        placeholderTextColor="#C4C4C4"
                                        value={email}
                                        onChangeText={(t: string) => {
                                            setEmail(t);
                                            if (errors.email) setErrors((e) => ({ ...e, email: undefined }));
                                        }}
                                        keyboardType="email-address"
                                        autoCapitalize="none"
                                        autoCorrect={false}
                                        fontSize={15}
                                    />
                                </Input>
                                {errors.email && (
                                    <Text fontSize={12} color="$red500" ml="$1">
                                        {errors.email}
                                    </Text>
                                )}
                            </VStack>

                            {/* Password */}
                            <VStack space="xs" mb="$5">
                                <Text fontSize={13} fontWeight="$medium" color="$coolGray600">
                                    Password
                                </Text>
                                <Input
                                    variant="outline"
                                    size="xl"
                                    borderRadius={14}
                                    borderColor={errors.password ? "$red400" : "$coolGray200"}
                                    bg="$coolGray50"
                                >
                                    <InputSlot pl="$3">
                                        <Lock
                                            size={18}
                                            color={errors.password ? "#F87171" : "#9CA3AF"}
                                        />
                                    </InputSlot>
                                    <InputField
                                        placeholder="Enter your password"
                                        placeholderTextColor="#C4C4C4"
                                        value={password}
                                        onChangeText={(t: string) => {
                                            setPassword(t);
                                            if (errors.password)
                                                setErrors((e) => ({ ...e, password: undefined }));
                                        }}
                                        type={showPassword ? "text" : "password"}
                                        fontSize={15}
                                    />
                                    <InputSlot
                                        pr="$3"
                                        onPress={() => setShowPassword(!showPassword)}
                                    >
                                        {showPassword ? (
                                            <EyeOff size={18} color="#9CA3AF" />
                                        ) : (
                                            <Eye size={18} color="#9CA3AF" />
                                        )}
                                    </InputSlot>
                                </Input>
                                {errors.password && (
                                    <Text fontSize={12} color="$red500" ml="$1">
                                        {errors.password}
                                    </Text>
                                )}
                            </VStack>

                            {/* Login Button */}
                            <Animated.View style={{ transform: [{ scale: buttonScale }] }}>
                                <Pressable
                                    onPress={handleLogin}
                                    onPressIn={onPressIn}
                                    onPressOut={onPressOut}
                                    disabled={isLoading}
                                    style={{
                                        backgroundColor: "#16a34a",
                                        borderRadius: 16,
                                        height: 54,
                                        alignItems: "center",
                                        justifyContent: "center",
                                        shadowColor: "#16a34a",
                                        shadowOffset: { width: 0, height: 6 },
                                        shadowOpacity: 0.3,
                                        shadowRadius: 12,
                                        elevation: 6,
                                    }}
                                >
                                    {isLoading ? (
                                        <ActivityIndicator color="#fff" />
                                    ) : (
                                        <Text
                                            color="$white"
                                            fontWeight="$bold"
                                            fontSize={16}
                                            letterSpacing={0.3}
                                        >
                                            Sign In
                                        </Text>
                                    )}
                                </Pressable>
                            </Animated.View>

                            {/* Divider */}
                            <HStack alignItems="center" my="$5">
                                <Box flex={1} h={1} bg="$coolGray100" />
                                <Text mx="$3" fontSize={13} color="$coolGray400">
                                    or continue with
                                </Text>
                                <Box flex={1} h={1} bg="$coolGray100" />
                            </HStack>

                            {/* Google Sign-In */}
                            <Pressable
                                onPress={handleGoogleSignIn}
                                style={{
                                    borderWidth: 1.5,
                                    borderColor: "#E5E7EB",
                                    borderRadius: 16,
                                    height: 54,
                                    flexDirection: "row",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    backgroundColor: "#fff",
                                }}
                            >
                                <Text fontSize={20} mr={8}>
                                    🔵
                                </Text>
                                <Text
                                    fontSize={15}
                                    fontWeight="$semibold"
                                    color="$coolGray700"
                                >
                                    Continue with Google
                                </Text>
                            </Pressable>
                        </Box>

                        {/* Sign Up Link */}
                        <HStack justifyContent="center" mt="$6" space="xs">
                            <Text fontSize={14} color="$coolGray400">
                                Don't have an account?
                            </Text>
                            <Pressable onPress={() => router.push("/(auth)/register")}>
                                <Text fontSize={14} fontWeight="$bold" color="$green600">
                                    Sign Up
                                </Text>
                            </Pressable>
                        </HStack>
                    </Animated.View>
                </ScrollView>
            </KeyboardAvoidingView>
        </SafeAreaView>
    );
}
