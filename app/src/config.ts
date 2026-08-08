import Constants from 'expo-constants';

// Where the backend lives.
//
// In development (Expo Go), we auto-derive the dev machine's LAN IP from the
// Expo dev server hostUri, so a phone and the laptop are automatically on the
// same host. To point at a deployed server instead, set "extra": { "apiUrl": "https://..." }
// in app.json (or leave the override blank to keep auto-detection).
const override = Constants.expoConfig?.extra?.apiUrl as string | undefined;

function defaultBaseUrl(): string {
  const hostUri = Constants.expoConfig?.hostUri;
  if (hostUri) {
    const host = hostUri.split(':')[0];
    return `http://${host}:8000`;
  }
  return 'http://127.0.0.1:8000';
}

export const API_URL: string = (override && override.length > 0 ? override : undefined) ?? defaultBaseUrl();

export const REACTION_EMOJIS = ['🔥', '😂', '🙌', '👀', '❤️'];
export const POST_MAX_LENGTH = 300;
