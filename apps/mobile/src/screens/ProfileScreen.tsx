import React, { useEffect, useState } from 'react';
import { StyleSheet, Text } from 'react-native';

import Card from '../components/Card';
import SectionHeader from '../components/SectionHeader';
import PrimaryButton from '../components/PrimaryButton';
import Screen from '../components/Screen';
import InputField from '../components/InputField';
import FadeInView from '../components/FadeInView';
import { apiRequest } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../hooks/useTranslation';
import { colors, spacing } from '../theme';

export default function ProfileScreen() {
  const { token } = useAuth();
  const { t } = useTranslation();
  const [profile, setProfile] = useState({ first_name: '', last_name: '', date_of_birth: '' });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const response = await apiRequest('/profile/profiles/me', { token });
        if (!response.ok) return;
        const data = await response.json();
        setProfile({
          first_name: data.first_name || '',
          last_name: data.last_name || '',
          date_of_birth: data.date_of_birth || '',
        });
      } catch {
        setError(t('profile.load_error'));
      }
    };
    fetchProfile();
  }, [token]);

  const handleSave = async () => {
    setMessage('');
    setError('');
    try {
      const response = await apiRequest('/profile/profiles/me', {
        method: 'PUT',
        token,
        body: JSON.stringify({
          first_name: profile.first_name,
          last_name: profile.last_name,
          date_of_birth: profile.date_of_birth || null,
        }),
      });
      if (!response.ok) throw new Error();
      setMessage(t('profile.saved_message'));
    } catch {
      setError(t('profile.save_error'));
    }
  };

  return (
    <Screen>
      <SectionHeader title={t('profile.title')} subtitle={t('profile.subtitle')} />
      <FadeInView>
        <Card>
          <InputField
            label={t('profile.first_name')}
            placeholder={t('profile.first_name')}
            value={profile.first_name}
            onChangeText={(value) => setProfile(prev => ({ ...prev, first_name: value }))}
          />
          <InputField
            label={t('profile.last_name')}
            placeholder={t('profile.last_name')}
            value={profile.last_name}
            onChangeText={(value) => setProfile(prev => ({ ...prev, last_name: value }))}
          />
          <InputField
            label={t('profile.date_of_birth')}
            placeholder={t('profile.date_of_birth')}
            value={profile.date_of_birth}
            onChangeText={(value) => setProfile(prev => ({ ...prev, date_of_birth: value }))}
          />
          <PrimaryButton title={t('common.save')} onPress={handleSave} />
          {message ? <Text style={styles.message}>{message}</Text> : null}
          {error ? <Text style={styles.error}>{error}</Text> : null}
        </Card>
      </FadeInView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  message: {
    marginTop: spacing.md,
    color: colors.success,
  },
  error: {
    marginTop: spacing.md,
    color: colors.danger,
  },
});
