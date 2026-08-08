import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Crypto from 'expo-crypto';

export interface Identity {
  deviceId: string;
  token: string;
}

const KEY = 'zona.identity.v1';

export function newDeviceId(): string {
  return Crypto.randomUUID();
}

export async function loadIdentity(): Promise<Identity | null> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    if (!raw) return null;
    return JSON.parse(raw) as Identity;
  } catch {
    return null;
  }
}

export async function saveIdentity(identity: Identity): Promise<void> {
  try {
    await AsyncStorage.setItem(KEY, JSON.stringify(identity));
  } catch {
    // storage full / unavailable — the session still works in memory
  }
}
