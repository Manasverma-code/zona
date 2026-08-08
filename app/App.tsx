import { useCallback, useEffect, useRef, useState } from 'react';
import { Alert, AppState, Pressable, StyleSheet, Text, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';

import * as api from './src/api';
import { ApiError } from './src/api';
import { BlankGate } from './src/components/BlankGate';
import { ComposerModal } from './src/components/ComposerModal';
import { Feed } from './src/components/Feed';
import { NewServerModal } from './src/components/NewServerModal';
import { ServerRail } from './src/components/ServerRail';
import { newDeviceId, loadIdentity, saveIdentity, type Identity } from './src/identity';
import { collectEvidence } from './src/location';
import { theme } from './src/theme';
import type { GateStatus, Post, Server } from './src/types';

type Gate = 'booting' | 'outside' | 'inside';

const POLL_MS = 15_000;

export default function App() {
  const [gate, setGate] = useState<Gate>('booting');
  const [handle, setHandle] = useState('');
  const [streak, setStreak] = useState(0);
  const [servers, setServers] = useState<Server[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [posts, setPosts] = useState<Post[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [composerOpen, setComposerOpen] = useState(false);
  const [newServerOpen, setNewServerOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const identityRef = useRef<Identity | null>(null);
  const selectedIdRef = useRef<number | null>(null);
  selectedIdRef.current = selectedId;

  const selectedServer = servers.find((s) => s.id === selectedId) ?? null;

  const refresh = useCallback(async (silent = false) => {
    const identity = identityRef.current;
    if (!identity) return;

    if (!silent) setRefreshing(true);
    setError(null);

    const evidence = await collectEvidence();

    const handleGate = (gate: GateStatus | null) => {
      setGate(gate && gate.inside ? 'inside' : 'outside');
    };

    try {
      let res = await api.ping(identity.token, evidence);
      if (!res.gate.inside) {
        handleGate(res.gate);
        setPosts([]);
        return;
      }

      const [serverRes, feedRes] = await Promise.all([
        api.getServers(identity.token, evidence),
        api.getFeed(identity.token, evidence, selectedIdRef.current ?? undefined),
      ]);

      setServers(serverRes.servers);
      if (serverRes.servers.length > 0 && selectedIdRef.current == null) {
        const first = serverRes.servers.find((s) => s.is_default) ?? serverRes.servers[0];
        setSelectedId(first.id);
        const fresh = await api.getFeed(identity.token, evidence, first.id);
        setPosts(fresh.posts);
        setStreak(fresh.streak);
        setHandle(res.handle);
      } else {
        setPosts(feedRes.posts);
        setStreak(feedRes.streak);
        setHandle(res.handle);
      }
      handleGate(res.gate);
    } catch (e) {
      if (e instanceof ApiError && e.code === 'outside_zone') {
        setGate('outside');
        setPosts([]);
      } else if (e instanceof ApiError && e.status === 401) {
        await reauth(identity);
      } else if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError('Unexpected error');
      }
    } finally {
      setRefreshing(false);
    }
  }, []);

  const reauth = useCallback(async (identity: Identity) => {
    try {
      const evidence = await collectEvidence();
      const res = await api.register(identity.deviceId, evidence);
      const updated = { ...identity, token: res.token };
      identityRef.current = updated;
      await saveIdentity(updated);
      await refresh(true);
    } catch {
      setError("Can't reach the Zona server. Check your connection.");
    }
  }, [refresh]);

  const boot = useCallback(async () => {
    let identity = await loadIdentity();
    if (!identity) {
      identity = { deviceId: newDeviceId(), token: '' };
      try {
        const evidence = await collectEvidence();
        const res = await api.register(identity.deviceId, evidence);
        identity = { ...identity, token: res.token };
        await saveIdentity(identity);
      } catch (e) {
        if (e instanceof ApiError) {
          setError(e.message);
        }
      }
    }
    identityRef.current = identity;
    await refresh(true);
  }, [refresh]);

  useEffect(() => {
    boot();
  }, [boot]);

  useEffect(() => {
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active') refresh(true);
    });
    const timer = setInterval(() => {
      if (gate === 'inside') refresh(true);
    }, POLL_MS);
    return () => {
      sub.remove();
      clearInterval(timer);
    };
  }, [gate, refresh]);

  const selectServer = useCallback(async (id: number) => {
    setSelectedId(id);
    const identity = identityRef.current;
    if (!identity) return;
    try {
      const evidence = await collectEvidence();
      const res = await api.getFeed(identity.token, evidence, id);
      setPosts(res.posts);
    } catch (e) {
      if (e instanceof ApiError && e.code === 'outside_zone') setGate('outside');
      else if (e instanceof ApiError) setError(e.message);
    }
  }, []);

  const createPost = useCallback(async (body: string) => {
    const identity = identityRef.current;
    if (!identity || !selectedIdRef.current) throw new Error('No room selected');
    const evidence = await collectEvidence();
    await api.createPost(identity.token, evidence, selectedIdRef.current, body);
    await refresh(true);
  }, [refresh]);

  const createServer = useCallback(async (name: string, description: string) => {
    const identity = identityRef.current;
    if (!identity) throw new Error('Not registered');
    const evidence = await collectEvidence();
    const created = await api.createServer(identity.token, evidence, name, description);
    setServers((prev) => [created, ...prev]);
    setSelectedId(created.id);
    const res = await api.getFeed(identity.token, evidence, created.id);
    setPosts(res.posts);
  }, []);

  const react = useCallback(async (post: Post, emoji: string) => {
    const identity = identityRef.current;
    if (!identity) return;
    try {
      const evidence = await collectEvidence();
      const updated = await api.react(identity.token, evidence, post.id, emoji);
      setPosts((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
    } catch (e) {
      if (e instanceof ApiError) setError(e.message);
    }
  }, []);

  const reportPost = useCallback(async (post: Post) => {
    const identity = identityRef.current;
    if (!identity) return;
    try {
      const evidence = await collectEvidence();
      await api.reportPost(identity.token, evidence, post.id);
      Alert.alert('Reported', 'Thanks — the mods will look at it.');
    } catch (e) {
      if (e instanceof ApiError) setError(e.message);
    }
  }, []);

    const manageServer = useCallback(
      (server: Server) => {
        const identity = identityRef.current;
        if (!identity) return;
        const buttons: { text: string; style: 'cancel' | 'destructive'; onPress?: () => void }[] =
          [
            { text: 'Cancel', style: 'cancel' },
            {
              text: 'Report room',
              style: 'destructive',
              onPress: () => {
                (async () => {
                  try {
                    const evidence = await collectEvidence();
                    await api.reportServer(identity.token, evidence, server.id);
                    Alert.alert('Reported', 'Thanks — the mods will look at it.');
                  } catch (e) {
                    if (e instanceof ApiError) setError(e.message);
                  }
                })();
              },
            },
          ];
      if (server.is_creator) {
        buttons.push({
          text: 'Delete my room',
          style: 'destructive' as const,
          onPress: () => {
            Alert.alert('Delete room?', `"${server.name}" will disappear for everyone.`, [
              { text: 'Cancel', style: 'cancel' },
              {
                text: 'Delete',
                style: 'destructive',
                onPress: async () => {
                  try {
                    const evidence = await collectEvidence();
                    await api.deleteServer(identity.token, evidence, server.id);
                    setServers((prev) => prev.filter((s) => s.id !== server.id));
                    if (selectedIdRef.current === server.id) setSelectedId(null);
                  } catch (e) {
                    if (e instanceof ApiError) setError(e.message);
                  }
                },
              },
            ]);
          },
        });
      }
      Alert.alert(server.name, server.description || 'No description', buttons);
    },
    []
  );

  if (gate === 'booting') {
    return (
      <View style={styles.boot}>
        <StatusBar style="light" />
        <Text style={styles.bootText}>zona</Text>
        {error && (
          <View style={styles.bootErrorWrap}>
            <Text style={styles.bootError}>{error}</Text>
            <Pressable style={styles.bootRetry} onPress={() => boot()}>
              <Text style={styles.bootRetryText}>Retry</Text>
            </Pressable>
          </View>
        )}
      </View>
    );
  }

  if (gate === 'outside') {
    return (
      <View style={styles.root}>
        <StatusBar style="light" />
        <BlankGate hint={error} />
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <StatusBar style="light" />
      <View style={styles.header}>
        <Text style={styles.headerHandle}>{handle}</Text>
        {streak > 0 && <Text style={styles.headerStreak}>🔥 {streak} day{streak > 1 ? 's' : ''}</Text>}
        <Text style={styles.headerZone}>inside the zone</Text>
      </View>
      <ServerRail
        servers={servers}
        selectedId={selectedId}
        onSelect={selectServer}
        onCreatePress={() => setNewServerOpen(true)}
        onManage={manageServer}
      />
      <Feed
        posts={posts}
        refreshing={refreshing}
        onRefresh={() => refresh(true)}
        onReact={react}
        onReport={reportPost}
      />
      {error && (
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      )}
      <Pressable style={styles.composer} onPress={() => setComposerOpen(true)}>
        <Text style={styles.composerText}>What's happening? +</Text>
      </Pressable>
      <ComposerModal
        visible={composerOpen}
        server={selectedServer}
        onClose={() => setComposerOpen(false)}
        onSubmit={createPost}
      />
      <NewServerModal
        visible={newServerOpen}
        onClose={() => setNewServerOpen(false)}
        onSubmit={createServer}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: theme.bg,
  },
  boot: {
    flex: 1,
    backgroundColor: theme.bg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  bootText: {
    color: theme.accent,
    fontSize: 40,
    fontWeight: '800',
    letterSpacing: 2,
  },
  bootErrorWrap: {
    position: 'absolute',
    bottom: 120,
    left: 24,
    right: 24,
    alignItems: 'center',
  },
  bootError: {
    color: theme.danger,
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 14,
  },
  bootRetry: {
    backgroundColor: theme.accent,
    borderRadius: 20,
    paddingHorizontal: 28,
    paddingVertical: 10,
  },
  bootRetryText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 15,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 16,
    paddingTop: 14,
  },
  headerHandle: {
    color: theme.text,
    fontWeight: '700',
    fontSize: 15,
  },
  headerStreak: {
    color: theme.gold,
    fontSize: 13,
    fontWeight: '600',
  },
  headerZone: {
    marginLeft: 'auto',
    color: theme.success,
    fontSize: 12,
  },
  composer: {
    position: 'absolute',
    right: 18,
    bottom: 24,
    backgroundColor: theme.accent,
    borderRadius: 26,
    paddingHorizontal: 20,
    paddingVertical: 14,
    shadowColor: theme.accent,
    shadowOpacity: 0.4,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 6,
  },
  composerText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 15,
  },
  errorBanner: {
    position: 'absolute',
    left: 12,
    right: 12,
    bottom: 90,
    backgroundColor: '#3A1F22',
    borderRadius: 10,
    padding: 10,
  },
  errorText: {
    color: theme.danger,
    fontSize: 13,
    textAlign: 'center',
  },
});
