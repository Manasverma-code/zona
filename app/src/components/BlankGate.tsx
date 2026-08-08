import { StyleSheet, Text, View } from 'react-native';
import { theme } from '../theme';

export function BlankGate({ hint }: { hint?: string | null }) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>You're outside the zone.</Text>
      <Text style={styles.subtitle}>
        {hint ?? 'Nothing to see.'}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.bg,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
  },
  title: {
    color: theme.text,
    fontSize: 22,
    fontWeight: '700',
    textAlign: 'center',
  },
  subtitle: {
    color: theme.textDim,
    fontSize: 15,
    marginTop: 8,
    textAlign: 'center',
  },
});
