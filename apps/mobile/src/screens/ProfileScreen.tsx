import React, { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, TextInput, Text } from 'react-native';

import Card from '../components/Card';
import SectionHeader from '../components/SectionHeader';
import PrimaryButton from '../components/PrimaryButton';
import { apiRequest } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../hooks/useTranslation';

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
      setError('Failed to load profile.');
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
      setMessage(t('common.save'));
    } catch {
      setError('Failed to save profile.');
    }
  };

  return (
    <ScrollView style={styles.container}>
      <SectionHeader title={t('profile.title')} subtitle={t('profile.subtitle')} />
      <Card>
        <TextInput
          style={styles.input}
          placeholder={t('profile.first_name')}
          value={profile.first_name}
          onChangeText={(value) => setProfile(prev => ({ ...prev, first_name: value }))}
        />
        <TextInput
          style={styles.input}
          placeholder={t('profile.last_name')}
          value={profile.last_name}
          onChangeText={(value) => setProfile(prev => ({ ...prev, last_name: value }))}
        />
        <TextInput
          style={styles.input}
          placeholder={t('profile.date_of_birth')}
          value={profile.date_of_birth}
          onChangeText={(value) => setProfile(prev => ({ ...prev, date_of_birth: value }))}
        />
        <PrimaryButton title={t('common.save')} onPress={handleSave} />
        {message ? <Text style={styles.message}>{message}</Text> : null}
        {error ? <Text style={styles.error}>{error}</Text> : null}
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
  },
  input: {
    backgroundColor: '#f8fafc',
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    marginBottom: 12,
  },
  message: {
    marginTop: 12,
    color: '#16a34a',
  },
  error: {
    marginTop: 12,
    color: '#dc2626',
  },
});
