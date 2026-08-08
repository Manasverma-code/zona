import { Alert, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { Server } from '../types';
import { theme } from '../theme';

interface Props {
  servers: Server[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onCreatePress: () => void;
  onManage: (server: Server) => void;
}

export function ServerRail({ servers, selectedId, onSelect, onCreatePress, onManage }: Props) {
  const ordered = [
    ...servers.filter((s) => s.is_default),
    ...servers.filter((s) => !s.is_default),
  ];

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.rail}
    >
      {ordered.map((server) => {
        const selected = server.id === selectedId;
        return (
          <TouchableOpacity
            key={server.id}
            style={[styles.chip, selected && styles.chipSelected]}
            onPress={() => onSelect(server.id)}
            onLongPress={() => onManage(server)}
          >
            <Text style={[styles.chipText, selected && styles.chipTextSelected]} numberOfLines={1}>
              {server.name}
            </Text>
            <Text style={[styles.chipCount, selected && styles.chipCountSelected]}>
              {server.post_count}
            </Text>
          </TouchableOpacity>
        );
      })}
      <TouchableOpacity style={styles.addChip} onPress={onCreatePress}>
        <Text style={styles.addText}>+</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  rail: {
    paddingHorizontal: 12,
    paddingVertical: 10,
    gap: 8,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: theme.card,
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 8,
    maxWidth: 180,
  },
  chipSelected: {
    backgroundColor: theme.accentSoft,
    borderColor: theme.accent,
  },
  chipText: {
    color: theme.text,
    fontSize: 14,
    fontWeight: '600',
    maxWidth: 120,
  },
  chipTextSelected: {
    color: theme.accent,
  },
  chipCount: {
    color: theme.textDim,
    fontSize: 12,
  },
  chipCountSelected: {
    color: theme.accent,
  },
  addChip: {
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: 1,
    borderStyle: 'dashed',
    borderColor: theme.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  addText: {
    color: theme.accent,
    fontSize: 20,
    lineHeight: 24,
  },
});
