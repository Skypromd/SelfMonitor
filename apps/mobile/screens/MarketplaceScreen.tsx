import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  FlatList,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, spacing, fontSize } from '../theme';
import { apiCall } from '../api';

type Partner = {
  id: string;
  name: string;
  description: string;
  category: string;
};

export default function MarketplaceScreen() {
  const [partners, setPartners] = useState<Partner[]>([]);
  const [loading, setLoading] = useState(true);
  const [handoffLoading, setHandoffLoading] = useState<string | null>(null);

  const fetchPartners = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiCall('/partners/partners');
      if (!res.ok) throw new Error('Failed to fetch partners');
      const data = await res.json();
      setPartners(Array.isArray(data) ? data : data.partners || []);
    } catch (err: any) {
      Alert.alert('Error', err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPartners();
  }, [fetchPartners]);

  const requestContact = useCallback(async (partnerId: string) => {
    setHandoffLoading(partnerId);
    try {
      const res = await apiCall(`/partners/partners/${partnerId}/handoff`, {
        method: 'POST',
        body: JSON.stringify({}),
      });
      if (!res.ok) throw new Error('Failed to request contact');
      Alert.alert('Success', 'Contact request sent. The partner will reach out soon.');
    } catch (err: any) {
      Alert.alert('Error', err.message);
    } finally {
      setHandoffLoading(null);
    }
  }, []);

  const renderPartner = ({ item }: { item: Partner }) => (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Text style={styles.partnerName}>{item.name}</Text>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{item.category}</Text>
        </View>
      </View>
      <Text style={styles.partnerDescription}>{item.description}</Text>
      <TouchableOpacity
        style={styles.button}
        onPress={() => requestContact(item.id)}
        disabled={handoffLoading === item.id}
      >
        {handoffLoading === item.id ? (
          <ActivityIndicator color={colors.text} />
        ) : (
          <Text style={styles.buttonText}>Request Contact</Text>
        )}
      </TouchableOpacity>
    </View>
  );

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Marketplace</Text>
        <Text style={styles.subtitle}>Find professional partners</Text>
      </View>

      {loading ? (
        <ActivityIndicator size="large" color={colors.accentTeal} style={styles.loader} />
      ) : (
        <FlatList
          data={partners}
          keyExtractor={(item) => item.id}
          renderItem={renderPartner}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            <Text style={styles.emptyText}>No partners available.</Text>
          }
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  header: {
    padding: spacing.md,
    paddingBottom: spacing.sm,
  },
  title: {
    fontSize: fontSize.xl,
    fontWeight: '700',
    color: colors.text,
  },
  subtitle: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
  list: {
    padding: spacing.md,
    paddingTop: 0,
  },
  card: {
    backgroundColor: colors.bgElevated,
    borderRadius: 12,
    padding: spacing.lg,
    marginBottom: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  partnerName: {
    fontSize: fontSize.lg,
    fontWeight: '600',
    color: colors.text,
    flex: 1,
  },
  badge: {
    backgroundColor: colors.accentGold,
    borderRadius: 12,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  badgeText: {
    fontSize: fontSize.xs,
    color: colors.text,
    fontWeight: '600',
  },
  partnerDescription: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginBottom: spacing.md,
    lineHeight: 20,
  },
  button: {
    backgroundColor: colors.accentTeal,
    borderRadius: 8,
    padding: spacing.md,
    alignItems: 'center',
  },
  buttonText: {
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  loader: {
    marginTop: spacing.xl,
  },
  emptyText: {
    color: colors.textMuted,
    fontSize: fontSize.sm,
    textAlign: 'center',
    marginTop: spacing.xl,
  },
});
