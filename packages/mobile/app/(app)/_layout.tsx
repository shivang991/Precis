import { Stack, Redirect } from 'expo-router';

import { SafeAreaView } from 'react-native-safe-area-context';

import { useAuthStore } from '../../store/auth';

export default function AppLayout() {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Redirect href="/(auth)/login" />;

  return (
    <SafeAreaView style={{ flex: 1 }}>
      <Stack screenOptions={{ headerShown: false }} />
    </SafeAreaView>
  );
}
