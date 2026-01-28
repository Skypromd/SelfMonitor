import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import * as ImagePicker from 'expo-image-picker';
import AsyncStorage from '@react-native-async-storage/async-storage';

import Card from '../components/Card';
import SectionHeader from '../components/SectionHeader';
import PrimaryButton from '../components/PrimaryButton';
import GradientCard from '../components/GradientCard';
import Screen from '../components/Screen';
import ListItem from '../components/ListItem';
import Badge from '../components/Badge';
import EmptyState from '../components/EmptyState';
import FadeInView from '../components/FadeInView';
import InfoRow from '../components/InfoRow';
import { useTranslation } from '../hooks/useTranslation';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import { apiRequest } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { colors, spacing } from '../theme';

type DocumentItem = {
  id: string;
  filename: string;
  status: 'processing' | 'completed' | 'failed';
  uploaded_at: string;
  extracted_data?: {
    total_amount?: number;
    vendor_name?: string;
    transaction_date?: string;
  } | null;
};

type PickedFile = {
  uri: string;
  name: string;
  mimeType: string;
};

export default function DocumentsScreen() {
  const { t } = useTranslation();
  const { token } = useAuth();
  const { isOffline } = useNetworkStatus();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [lastSync, setLastSync] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchDocuments = async () => {
    try {
      const response = await apiRequest('/documents', { token });
      if (!response.ok) return;
      const data = await response.json();
      setDocuments(data || []);
      setLastSync(new Date().toISOString());
      try {
        await AsyncStorage.setItem('documents.cache', JSON.stringify(data || []));
      } catch {
        return;
      }
    } catch {
      setDocuments([]);
    }
  };

  useEffect(() => {
    const loadCached = async () => {
      try {
        const cached = await AsyncStorage.getItem('documents.cache');
        if (cached) {
          setDocuments(JSON.parse(cached));
        }
      } catch {
        return;
      }
    };
    loadCached();
    fetchDocuments();
  }, [token]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await fetchDocuments();
    setIsRefreshing(false);
  };

  const statusTone = (status: DocumentItem['status']) => {
    if (status === 'completed') return 'success';
    if (status === 'failed') return 'danger';
    return 'warning';
  };

  const statusLabel = (status: DocumentItem['status']) => {
    if (status === 'completed') return t('documents.status_completed');
    if (status === 'failed') return t('documents.status_failed');
    return t('documents.status_processing');
  };

  const formatSubtitle = (doc: DocumentItem) => {
    if (doc.extracted_data?.vendor_name) {
      return `${doc.extracted_data.vendor_name} · ${doc.filename}`;
    }
    return doc.filename;
  };
  const lastSyncLabel = lastSync ? new Date(lastSync).toLocaleString() : t('common.not_available');
  const processingCount = documents.filter((doc) => doc.status === 'processing').length;
  const failedCount = documents.filter((doc) => doc.status === 'failed').length;

  const uploadFile = async (file: PickedFile) => {
    setMessage('');
    setError('');
    try {
      setIsUploading(true);
      const formData = new FormData();
      formData.append('file', {
        uri: file.uri,
        name: file.name,
        type: file.mimeType,
      } as any);
      const response = await apiRequest('/documents/upload', {
        method: 'POST',
        token,
        body: formData,
      });
      if (!response.ok) throw new Error(t('documents.upload_error'));
      setMessage(t('documents.upload_success'));
      fetchDocuments();
    } catch (err: any) {
      setError(err.message || t('documents.upload_error'));
    } finally {
      setIsUploading(false);
    }
  };

  const handleScan = async () => {
    setMessage('');
    setError('');
    if (isOffline) {
      setError(t('documents.offline_error'));
      return;
    }
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      setError(t('documents.camera_error'));
      return;
    }
    const result = await ImagePicker.launchCameraAsync({
      quality: 0.7,
    });
    if (result.canceled) return;
    const asset = result.assets[0];
    await uploadFile({
      uri: asset.uri,
      name: asset.fileName || `receipt-${Date.now()}.jpg`,
      mimeType: asset.mimeType || 'image/jpeg',
    });
  };

  const handleUpload = async () => {
    setMessage('');
    setError('');
    if (isOffline) {
      setError(t('documents.offline_error'));
      return;
    }
    const result = await DocumentPicker.getDocumentAsync({
      type: ['image/*', 'application/pdf'],
    });
    if (result.canceled) return;
    const asset = result.assets[0];
    await uploadFile({
      uri: asset.uri,
      name: asset.name || `document-${Date.now()}`,
      mimeType: asset.mimeType || 'application/octet-stream',
    });
  };

  return (
    <Screen refreshing={isRefreshing} onRefresh={handleRefresh}>
      <GradientCard colors={['#0f172a', '#1e293b']}>
        <Text style={styles.heroTitle}>{t('documents.title')}</Text>
        <Text style={styles.heroSubtitle}>{t('documents.subtitle')}</Text>
      </GradientCard>
      <FadeInView>
        <Card>
          <Text style={styles.cardTitle}>{t('documents.scan_button')}</Text>
          <PrimaryButton
            title={isUploading ? t('documents.uploading') : t('documents.scan_button')}
            onPress={handleScan}
            disabled={isUploading || isOffline}
            haptic="medium"
          />
          <View style={styles.divider} />
          <PrimaryButton
            title={t('documents.upload_button')}
            onPress={handleUpload}
            variant="secondary"
            disabled={isUploading || isOffline}
            haptic="medium"
          />
          {message ? <Text style={styles.message}>{message}</Text> : null}
          {error ? <Text style={styles.error}>{error}</Text> : null}
        </Card>
      </FadeInView>

      <FadeInView delay={80}>
        <Card>
          <Text style={styles.cardTitle}>{t('documents.tips_title')}</Text>
          <ListItem
            title={t('documents.tip_light')}
            subtitle={t('documents.tip_light_subtitle')}
            icon="sunny-outline"
          />
          <ListItem
            title={t('documents.tip_flat')}
            subtitle={t('documents.tip_flat_subtitle')}
            icon="scan-outline"
          />
          <ListItem
            title={t('documents.tip_notes')}
            subtitle={t('documents.tip_notes_subtitle')}
            icon="bookmark-outline"
          />
        </Card>
      </FadeInView>

      <SectionHeader title={t('documents.recent_title')} subtitle={t('documents.recent_subtitle')} />
      <FadeInView delay={120}>
        <Card>
          <View style={styles.summaryRow}>
            <InfoRow label={t('common.last_sync')} value={lastSyncLabel} />
          </View>
          <View style={styles.badgeRow}>
            {processingCount ? (
              <View style={styles.badgeItem}>
                <Badge label={`${processingCount} ${t('documents.status_processing')}`} tone="warning" />
              </View>
            ) : null}
            {failedCount ? (
              <View style={styles.badgeItem}>
                <Badge label={`${failedCount} ${t('documents.status_failed')}`} tone="danger" />
              </View>
            ) : null}
          </View>
          {documents.length === 0 ? (
            <EmptyState
              title={t('documents.empty_title')}
              subtitle={t('documents.empty_subtitle')}
              icon="document-text-outline"
            />
          ) : (
            documents.map(doc => (
              <ListItem
                key={doc.id}
                title={formatSubtitle(doc)}
                subtitle={doc.uploaded_at}
                icon="document-text-outline"
                badge={<Badge label={statusLabel(doc.status)} tone={statusTone(doc.status)} />}
                meta={doc.extracted_data?.total_amount ? `GBP ${doc.extracted_data.total_amount.toFixed(2)}` : undefined}
              />
            ))
          )}
        </Card>
      </FadeInView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  heroTitle: {
    color: colors.surface,
    fontSize: 26,
    fontWeight: '700',
  },
  heroSubtitle: {
    color: '#cbd5f5',
    marginTop: spacing.xs,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: spacing.sm,
    color: colors.textPrimary,
  },
  summaryRow: {
    marginBottom: spacing.sm,
  },
  badgeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: spacing.sm,
  },
  badgeItem: {
    marginRight: spacing.sm,
    marginBottom: spacing.sm,
  },
  divider: {
    height: spacing.md,
  },
  message: {
    marginTop: spacing.md,
    color: colors.success,
  },
  error: {
    marginTop: spacing.md,
    color: colors.danger,
  },
});
