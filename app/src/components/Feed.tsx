import { FlatList, RefreshControl, StyleSheet, Text, View } from 'react-native';
import type { Post } from '../types';
import { PostCard } from './PostCard';
import { theme } from '../theme';

interface Props {
  posts: Post[];
  refreshing: boolean;
  onRefresh: () => void;
  onReact: (post: Post, emoji: string) => void;
  onReport: (post: Post) => void;
}

export function Feed({ posts, refreshing, onRefresh, onReact, onReport }: Props) {
  if (posts.length === 0) {
    return (
      <View style={styles.emptyWrap}>
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        <Text style={styles.emptyTitle}>Nothing here yet.</Text>
        <Text style={styles.emptySub}>Be the first. Posts evaporate in 24 hours.</Text>
      </View>
    );
  }

  return (
    <FlatList
      data={posts}
      keyExtractor={(p) => String(p.id)}
      renderItem={({ item }) => (
        <PostCard post={item} onReact={onReact} onReport={onReport} />
      )}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      contentContainerStyle={styles.list}
      style={styles.scroll}
    />
  );
}

const styles = StyleSheet.create({
  scroll: {
    flex: 1,
  },
  list: {
    paddingVertical: 8,
  },
  emptyWrap: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  emptyTitle: {
    color: theme.text,
    fontSize: 17,
    fontWeight: '600',
  },
  emptySub: {
    color: theme.textDim,
    fontSize: 13,
    marginTop: 6,
    textAlign: 'center',
  },
});
