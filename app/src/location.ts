import * as Crypto from 'expo-crypto';
import * as Location from 'expo-location';

// Everything the phone tells the server about where it is, on every request.
export interface Evidence {
  lat: number | null;
  lon: number | null;
  fixEpoch: number | null; // unix seconds of the GPS measurement
  accuracy: number | null; // meters
  bssidHashes: string[]; // sha256 hashes of visible campus Wi-Fi APs (may be empty)
}

const EMPTY: Evidence = {
  lat: null,
  lon: null,
  fixEpoch: null,
  accuracy: null,
  bssidHashes: [],
};

export async function collectEvidence(): Promise<Evidence> {
  try {
    let perm = await Location.getForegroundPermissionsAsync();
    if (!perm.granted) {
      perm = await Location.requestForegroundPermissionsAsync();
      if (!perm.granted) return EMPTY;
    }

    // getCurrentPositionAsync can wait for a GPS fix indefinitely; race it
    // against a timer so the boot screen can never hang on no-fix.
    const pos = await Promise.race([
      Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High }),
      new Promise<null>((resolve) => setTimeout(() => resolve(null), 8_000)),
    ]);
    if (!pos) return EMPTY; // no fix in 8s → report no position

    return {
      lat: pos.coords.latitude,
      lon: pos.coords.longitude,
      fixEpoch: Math.floor(pos.timestamp / 1000),
      accuracy: pos.coords.accuracy,
      bssidHashes: await collectBssids(),
    };
  } catch {
    return EMPTY;
  }
}

// The server demands 64-char sha256 hex hashes of BSSIDs (see verify.py).
export function hashBssid(bssid: string): Promise<string> {
  return Crypto.digestStringAsync(
    Crypto.CryptoDigestAlgorithm.SHA256,
    bssid.trim().toUpperCase()
  );
}

// Expo Go has no BSSID API, so this returns nothing for now and the server's
// REQUIRE_BSSID_PROOF stays off. When the pilot moves to a development build,
// drop the wifi module in here (Android: WifiManager connection info → BSSID)
// and hash every visible AP with hashBssid().
async function collectBssids(): Promise<string[]> {
  return [];
}
