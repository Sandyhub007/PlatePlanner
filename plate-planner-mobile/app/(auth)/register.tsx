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
import {
    Mail,
    Lock,
    Eye,
    EyeOff,
    User,
    ArrowLeft,
    Check,
} from "lucide-react-native";
import { useAuth } from "../../src/state/auth";

export default function RegisterScreen() {
    const [fullName, setFullName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [errors, setErrors] = useState<{
        fullName?: string;
        email?: string;
        password?: string;
        confirmPassword?: string;
    }>({});

    const router = useRouter();
    const { register, loginWithGoogle } = useAuth();

    // Animations
    const headerOpacity = useRef(new Animated.Value(0)).current;
    const headerTranslateY = useRef(new Animated.Value(-20)).current;
    const formOpacity = useRef(new Animated.Value(0)).current;
    const formTranslateY = useRef(new Animated.Value(30)).current;
    const buttonScale = useRef(new Animated.Value(1)).current;

    useEffect(() => {
        Animated.sequence([
            Animated.parallel([
                Animated.timing(headerOpacity, {
                    toValue: 1,
                    duration: 400,
                    useNativeDriver: true,
                }),
                Animated.timing(headerTranslateY, {
                    toValue: 0,
                    duration: 400,
                    useNativeDriver: true,
                }),
            ]),
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

    // Password strength
    const passwordStrength = (() => {
        if (!password) return { level: 0, label: "", color: "#E5E7EB" };
        let score = 0;
        if (password.length >= 8) score++;
        if (/[A-Z]/.test(password)) score++;
        if (/[0-9]/.test(password)) score++;
        if (/[^A-Za-z0-9]/.test(password)) score++;

        if (score <= 1) return { level: 1, label: "Weak", color: "#EF4444" };
        if (score === 2) return { level: 2, label: "Fair", color: "#F59E0B" };
        if (score === 3) return { level: 3, label: "Good", color: "#86C649" };
        return { level: 4, label: "Strong", color: "#22C55E" };
    })();

    const validate = () => {
        const newErrors: typeof errors = {};
        if (!fullName.trim()) newErrors.fullName = "Full name is required";
        if (!email.trim()) {
            newErrors.email = "Email is required";
        } else if (!/\S+@\S+\.\S+/.test(email)) {
            newErrors.email = "Enter a valid email address";
        }
        if (!password) {
            newErrors.password = "Password is required";
        } else if (password.length < 8) {
            newErrors.password = "Password must be at least 8 characters";
        }
        if (!confirmPassword) {
            newErrors.confirmPassword = "Please confirm your password";
        } else if (password !== confirmPassword) {
            newErrors.confirmPassword = "Passwords do not match";
        }
        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleRegister = async () => {
        if (!validate()) return;
        setIsLoading(true);
        try {
            await register(email.trim(), password, fullName.trim());
            // AuthGate handles redirect on successful register + auto-login
        } catch (e: any) {
            console.error("Registration failed:", e);
            let errorMsg = e?.message || "Something went wrong. Please check your connection and try again.";

            if (errorMsg.includes("400")) {
                errorMsg = "This email is already registered. Try signing in instead.";
            }

            // Show status code if available for debugging
            const status = e?.status ? ` (Status: ${e.status})` : "";

            Alert.alert("Registration Failed", `${errorMsg}${status}`);
        } finally {
            setIsLoading(false);
        }
    };

    const handleGoogleSignUp = async () => {
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
                        paddingHorizontal: 24,
                        paddingBottom: 40,
                    }}
                    keyboardShouldPersistTaps="handled"
                    showsVerticalScrollIndicator={false}
                >
                    {/* Back Button */}
                    <Animated.View
                        style={{
                            opacity: headerOpacity,
                            transform: [{ translateY: headerTranslateY }],
                            marginTop: 8,
                        }}
                    >
                        <Pressable
                            onPress={() => router.back()}
                            style={{
                                width: 44,
                                height: 44,
                                borderRadius: 14,
                                backgroundColor: "#fff",
                                alignItems: "center",
                                justifyContent: "center",
                                borderWidth: 1,
                                borderColor: "#F3F4F6",
                                shadowColor: "#000",
                                shadowOffset: { width: 0, height: 2 },
                                shadowOpacity: 0.04,
                                shadowRadius: 8,
                                elevation: 2,
                            }}
                        >
                            <ArrowLeft size={20} color="#1F2937" />
                        </Pressable>
                    </Animated.View>

                    {/* Header */}
                    <Animated.View
                        style={{
                            opacity: headerOpacity,
                            transform: [{ translateY: headerTranslateY }],
                            marginTop: 24,
                            marginBottom: 24,
                        }}
                    >
                        <Text fontSize={30} fontWeight="$bold" color="$coolGray900">
                            Create Account
                        </Text>
                        <Text fontSize={15} color="$coolGray400" mt="$1">
                            Start your personalized meal planning journey
                        </Text>
                    </Animated.View>

                    {/* Form Card */}
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
                            {/* Full Name */}
                            <VStack space="xs" mb="$4">
                                <Text fontSize={13} fontWeight="$medium" color="$coolGray600">
                                    Full Name
                                </Text>
                                <Input
                                    variant="outline"
                                    size="xl"
                                    borderRadius={14}
                                    borderColor={errors.fullName ? "$red400" : "$coolGray200"}
                                    bg="$coolGray50"
                                >
                                    <InputSlot pl="$3">
                                        <User
                                            size={18}
                                            color={errors.fullName ? "#F87171" : "#9CA3AF"}
                                        />
                                    </InputSlot>
                                    <InputField
                                        placeholder="John Doe"
                                        placeholderTextColor="#C4C4C4"
                                        value={fullName}
                                        onChangeText={(t: string) => {
                                            setFullName(t);
                                            if (errors.fullName)
                                                setErrors((e) => ({ ...e, fullName: undefined }));
                                        }}
                                        autoCapitalize="words"
                                        fontSize={15}
                                    />
                                </Input>
                                {errors.fullName && (
                                    <Text fontSize={12} color="$red500" ml="$1">
                                        {errors.fullName}
                                    </Text>
                                )}
                            </VStack>

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
                                            if (errors.email)
                                                setErrors((e) => ({ ...e, email: undefined }));
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
                            <VStack space="xs" mb="$3">
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
                                        placeholder="Min. 8 characters"
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

                                {/* Password Strength Indicator */}
                                {password.length > 0 && (
                                    <VStack mt="$2" space="xs">
                                        <HStack space="xs">
                                            {[1, 2, 3, 4].map((level) => (
                                                <Box
                                                    key={level}
                                                    flex={1}
                                                    h={4}
                                                    borderRadius={2}
                                                    bg={
                                                        passwordStrength.level >= level
                                                            ? passwordStrength.color
                                                            : "#E5E7EB"
                                                    }
                                                />
                                            ))}
                                        </HStack>
                                        <Text fontSize={11} color={passwordStrength.color}>
                                            {passwordStrength.label}
                                        </Text>
                                    </VStack>
                                )}
                            </VStack>

                            {/* Confirm Password */}
                            <VStack space="xs" mb="$5">
                                <Text fontSize={13} fontWeight="$medium" color="$coolGray600">
                                    Confirm Password
                                </Text>
                                <Input
                                    variant="outline"
                                    size="xl"
                                    borderRadius={14}
                                    borderColor={
                                        errors.confirmPassword ? "$red400" : "$coolGray200"
                                    }
                                    bg="$coolGray50"
                                >
                                    <InputSlot pl="$3">
                                        <Lock
                                            size={18}
                                            color={errors.confirmPassword ? "#F87171" : "#9CA3AF"}
                                        />
                                    </InputSlot>
                                    <InputField
                                        placeholder="Repeat your password"
                                        placeholderTextColor="#C4C4C4"
                                        value={confirmPassword}
                                        onChangeText={(t: string) => {
                                            setConfirmPassword(t);
                                            if (errors.confirmPassword)
                                                setErrors((e) => ({
                                                    ...e,
                                                    confirmPassword: undefined,
                                                }));
                                        }}
                                        type={showConfirm ? "text" : "password"}
                                        fontSize={15}
                                    />
                                    <InputSlot
                                        pr="$3"
                                        onPress={() => setShowConfirm(!showConfirm)}
                                    >
                                        {showConfirm ? (
                                            <EyeOff size={18} color="#9CA3AF" />
                                        ) : (
                                            <Eye size={18} color="#9CA3AF" />
                                        )}
                                    </InputSlot>
                                </Input>
                                {errors.confirmPassword && (
                                    <Text fontSize={12} color="$red500" ml="$1">
                                        {errors.confirmPassword}
                                    </Text>
                                )}
                                {/* Match indicator */}
                                {confirmPassword.length > 0 &&
                                    !errors.confirmPassword &&
                                    password === confirmPassword && (
                                        <HStack alignItems="center" space="xs" mt="$1" ml="$1">
                                            <Check size={14} color="#22C55E" />
                                            <Text fontSize={11} color="#22C55E">
                                                Passwords match
                                            </Text>
                                        </HStack>
                                    )}
                            </VStack>

                            {/* Register Button */}
                            <Animated.View style={{ transform: [{ scale: buttonScale }] }}>
                                <Pressable
                                    onPress={handleRegister}
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
                                            Create Account
                                        </Text>
                                    )}
                                </Pressable>
                            </Animated.View>

                            {/* Divider */}
                            <HStack alignItems="center" my="$5">
                                <Box flex={1} h={1} bg="$coolGray100" />
                                <Text mx="$3" fontSize={13} color="$coolGray400">
                                    or sign up with
                                </Text>
                                <Box flex={1} h={1} bg="$coolGray100" />
                            </HStack>

                            {/* Google Sign-Up */}
                            <Pressable
                                onPress={handleGoogleSignUp}
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

                        {/* Sign In Link */}
                        <HStack justifyContent="center" mt="$6" space="xs">
                            <Text fontSize={14} color="$coolGray400">
                                Already have an account?
                            </Text>
                            <Pressable onPress={() => router.back()}>
                                <Text fontSize={14} fontWeight="$bold" color="$green600">
                                    Sign In
                                </Text>
                            </Pressable>
                        </HStack>
                    </Animated.View>
                </ScrollView>
            </KeyboardAvoidingView>
        </SafeAreaView>
    );
}
