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
import { theme } from '../theme';

interface Props {
  visible: boolean;
  onClose: () => void;
  onSubmit: (name: string, description: string) => Promise<void>;
}

const MAX_NAME = 40;
const MAX_DESC = 160;

export function NewServerModal({ visible, onClose, onSubmit }: Props) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (name.trim().length < 3 || sending) return;
    setSending(true);
    setError(null);
    try {
      await onSubmit(name.trim(), description.trim());
      setName('');
      setDescription('');
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
          <Text style={styles.title}>Start a room</Text>
          <Text style={styles.subtitle}>Anyone on campus can see and post in it.</Text>
          <TextInput
            style={styles.input}
            value={name}
            onChangeText={setName}
            placeholder="Room name (e.g. Hostel Wing B)"
            placeholderTextColor={theme.textDim}
            maxLength={MAX_NAME}
          />
          <TextInput
            style={[styles.input, styles.inputDesc]}
            value={description}
            onChangeText={setDescription}
            placeholder="What's it for? (optional)"
            placeholderTextColor={theme.textDim}
            maxLength={MAX_DESC}
          />
          <View style={styles.row}>
            {error && <Text style={styles.error}>{error}</Text>}
            <Pressable
              style={[styles.button, sending && styles.buttonDisabled]}
              disabled={sending || name.trim().length < 3}
              onPress={submit}
            >
              <Text style={styles.buttonText}>{sending ? '…' : 'Create room'}</Text>
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
  },
  subtitle: {
    color: theme.textDim,
    fontSize: 13,
    marginTop: 2,
    marginBottom: 14,
  },
  input: {
    color: theme.text,
    fontSize: 15,
    backgroundColor: theme.cardAlt,
    borderRadius: 12,
    padding: 12,
    marginBottom: 10,
  },
  inputDesc: {
    minHeight: 44,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
  },
  error: {
    color: theme.danger,
    fontSize: 12,
    flex: 1,
    marginRight: 10,
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
