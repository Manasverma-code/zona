import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { POST_MAX_LENGTH } from '../config';
import type { Server } from '../types';
import { theme } from '../theme';

interface Props {
  visible: boolean;
  server: Server | null;
  onClose: () => void;
  onSubmit: (body: string) => Promise<void>;
}

export function ComposerModal({ visible, server, onClose, onSubmit }: Props) {
  const [body, setBody] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (body.trim().length === 0 || sending) return;
    setSending(true);
    setError(null);
    try {
      await onSubmit(body.trim());
      setBody('');
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong');
    } finally {
      setSending(false);
    }
  };

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.overlay}
      >
        <Pressable style={styles.dismiss} onPress={onClose} />
        <View style={styles.sheet}>
          <Text style={styles.title}>
            Post in {server ? server.name : '…'}
          </Text>
          <TextInput
            style={styles.input}
            value={body}
            onChangeText={setBody}
            placeholder="What's happening on campus?"
            placeholderTextColor={theme.textDim}
            multiline
            maxLength={POST_MAX_LENGTH}
            autoFocus
          />
          <View style={styles.row}>
            <Text style={styles.count}>
              {body.length}/{POST_MAX_LENGTH}
            </Text>
            {error && <Text style={styles.error}>{error}</Text>}
            <Pressable
              style={[styles.button, sending && styles.buttonDisabled]}
              disabled={sending || body.trim().length === 0}
              onPress={submit}
            >
              <Text style={styles.buttonText}>{sending ? '…' : 'Post'}</Text>
            </Pressable>
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(0,0,0,0.6)',
  },
  dismiss: {
    flex: 1,
  },
  sheet: {
    backgroundColor: theme.card,
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
    padding: 18,
    paddingBottom: 32,
    borderWidth: 1,
    borderColor: theme.border,
  },
  title: {
    color: theme.text,
    fontWeight: '700',
    fontSize: 16,
    marginBottom: 12,
  },
  input: {
    color: theme.text,
    fontSize: 15,
    minHeight: 90,
    backgroundColor: theme.cardAlt,
    borderRadius: 12,
    padding: 12,
    textAlignVertical: 'top',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 10,
  },
  count: {
    color: theme.textDim,
    fontSize: 12,
  },
  error: {
    color: theme.danger,
    fontSize: 12,
    marginLeft: 10,
    flex: 1,
  },
  button: {
    backgroundColor: theme.accent,
    borderRadius: 20,
    paddingHorizontal: 22,
    paddingVertical: 9,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonText: {
    color: '#fff',
    fontWeight: '700',
  },
});
