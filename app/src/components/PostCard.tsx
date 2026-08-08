import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';
import type { Post } from '../types';
import { REACTION_EMOJIS } from '../config';
import { theme, timeAgo, timeLeft } from '../theme';

interface Props {
  post: Post;
  onReact: (post: Post, emoji: string) => void;
  onReport: (post: Post) => void;
}

export function PostCard({ post, onReact, onReport }: Props) {
  const openMenu = () => {
    Alert.alert('Post options', `By ${post.handle}`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Report', style: 'destructive', onPress: () => onReport(post) },
    ]);
  };

  return (
    <Pressable style={styles.card} onLongPress={openMenu} delayLongPress={400}>
      <View style={styles.header}>
        <Text style={styles.handle}>{post.handle}</Text>
        <Text style={styles.meta}>
          {timeAgo(post.created_at)} · dies in {timeLeft(post.expires_at)}
        </Text>
      </View>
      <Text style={styles.body}>{post.body}</Text>
      <View style={styles.actions}>
        {REACTION_EMOJIS.map((emoji) => {
          const count = post.reactions[emoji] ?? 0;
          const mine = post.my_reaction === emoji;
          return (
            <Pressable
              key={emoji}
              style={[styles.emoji, mine && styles.emojiMine]}
              onPress={() => onReact(post, emoji)}
            >
              <Text style={styles.emojiChar}>{emoji}</Text>
              {count > 0 && <Text style={styles.emojiCount}>{count}</Text>}
            </Pressable>
          );
        })}
        <Pressable style={styles.menuBtn} onPress={openMenu}>
          <Text style={styles.menuText}>⋯</Text>
        </Pressable>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.card,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: theme.border,
    padding: 14,
    marginHorizontal: 12,
    marginVertical: 6,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  handle: {
    color: theme.accent,
    fontWeight: '700',
    fontSize: 13,
  },
  meta: {
    color: theme.textDim,
    fontSize: 11,
  },
  body: {
    color: theme.text,
    fontSize: 15,
    lineHeight: 21,
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 10,
  },
  emoji: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: theme.cardAlt,
    borderRadius: 14,
    paddingHorizontal: 9,
    paddingVertical: 5,
  },
  emojiMine: {
    backgroundColor: theme.accentSoft,
    borderWidth: 1,
    borderColor: theme.accent,
  },
  emojiChar: {
    fontSize: 15,
  },
  emojiCount: {
    color: theme.textDim,
    fontSize: 12,
  },
  menuBtn: {
    marginLeft: 'auto',
    paddingHorizontal: 8,
  },
  menuText: {
    color: theme.textDim,
    fontSize: 18,
  },
});
