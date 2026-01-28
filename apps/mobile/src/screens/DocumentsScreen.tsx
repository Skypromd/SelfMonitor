import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import * as ImagePicker from 'expo-image-picker';

import Card from '../components/Card';
import SectionHeader from '../components/SectionHeader';
import PrimaryButton from '../components/PrimaryButton';
import GradientCard from '../components/GradientCard';
import Screen from '../components/Screen';
import ListItem from '../components/ListItem';
import Badge from '../components/Badge';
import EmptyState from '../components/EmptyState';
import FadeInView from '../components/FadeInView';
import { useTranslation } from '../hooks/useTranslation';
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
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isUploading, setIsUploading] = useState(false);

  const fetchDocuments = async () => {
    try {
      const response = await apiRequest('/documents', { token });
      if (!response.ok) return;
      const data = await response.json();
      setDocuments(data || []);
    } catch {
      setDocuments([]);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [token]);

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
    <Screen>
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
            disabled={isUploading}
          />
          <View style={styles.divider} />
          <PrimaryButton
            title={t('documents.upload_button')}
            onPress={handleUpload}
            variant="secondary"
            disabled={isUploading}
          />
          {message ? <Text style={styles.message}>{message}</Text> : null}
          {error ? <Text style={styles.error}>{error}</Text> : null}
        </Card>
      </FadeInView>

      <SectionHeader title={t('documents.recent_title')} subtitle={t('documents.recent_subtitle')} />
      <FadeInView delay={120}>
        <Card>
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
