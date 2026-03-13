/**
 * useOfflineCache — A simple hook that caches API responses in AsyncStorage.
 * On first load it shows cached data instantly, then refreshes from network.
 * Falls back to cached data if the network call fails.
 */
import { useState, useEffect, useCallback } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";

const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

interface CacheEntry<T> {
    data: T;
    timestamp: number;
}

export function useOfflineCache<T>(
    cacheKey: string,
    fetcher: () => Promise<T>,
    deps: any[] = []
) {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isStale, setIsStale] = useState(false);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);

        // ── 1. Show cached data immediately if available ──────────────────────
        try {
            const raw = await AsyncStorage.getItem(cacheKey);
            if (raw) {
                const cached: CacheEntry<T> = JSON.parse(raw);
                setData(cached.data);
                const age = Date.now() - cached.timestamp;
                if (age < CACHE_TTL_MS) {
                    // Fresh enough – skip network fetch
                    setLoading(false);
                    return;
                }
                setIsStale(true);
            }
        } catch (_) {
            // Ignore cache read errors
        }

        // ── 2. Fetch from network ─────────────────────────────────────────────
        try {
            const fresh = await fetcher();
            setData(fresh);
            setIsStale(false);
            // Persist to cache
            const entry: CacheEntry<T> = { data: fresh, timestamp: Date.now() };
            await AsyncStorage.setItem(cacheKey, JSON.stringify(entry));
        } catch (err: any) {
            setError(err?.message ?? "Network error");
            // Keep showing stale cached data if we have it
        } finally {
            setLoading(false);
        }
    }, [cacheKey, ...deps]);

    useEffect(() => {
        load();
    }, [load]);

    return { data, loading, error, isStale, refresh: load };
}

/** Invalidate a cache entry so the next load hits the network */
export async function invalidateCache(cacheKey: string) {
    await AsyncStorage.removeItem(cacheKey);
}

/** Clear all cached entries */
export async function clearAllCache() {
    const keys = await AsyncStorage.getAllKeys();
    const ppKeys = keys.filter((k) => k.startsWith("pp_"));
    if (ppKeys.length) await AsyncStorage.multiRemove(ppKeys);
}
