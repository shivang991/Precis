import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';

import { useRouter } from 'expo-router';

import { useAuthStore } from '../../store/auth';

export default function GeneralSettingsScreen() {
  const router = useRouter();
  const logout = useAuthStore((s) => s.logout);

  return (
    <View style={styles.container}>
      <TouchableOpacity
        style={styles.logoutBtn}
        onPress={() => {
          logout();
          router.replace('/(auth)/login');
        }}
      >
        <Text style={styles.logoutText}>Sign Out</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#fff' },
  logoutBtn: { marginTop: 'auto', padding: 16, alignItems: 'center' },
  logoutText: { fontSize: 15, color: '#e53935' },
});
