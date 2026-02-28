import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Home.module.css';

const API_GATEWAY_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';
const AUTH_SERVICE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8001';
const PROFILE_SERVICE_URL = process.env.NEXT_PUBLIC_PROFILE_SERVICE_URL || 'http://localhost:8005';

type ProfilePageProps = {
  token: string;
};

type UserProfile = {
  first_name: string;
  last_name: string;
  date_of_birth: string;
};

type TwoFASetup = {
  secret: string;
  provisioning_uri: string;
};

function getPasswordChecks(password: string) {
  return {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    digit: /\d/.test(password),
    special: /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?`~]/.test(password),
  };
}

function getStrength(checks: ReturnType<typeof getPasswordChecks>) {
  const passed = Object.values(checks).filter(Boolean).length;
  if (passed >= 5) return 'strong';
  if (passed >= 3) return 'medium';
  return 'weak';
}

export default function ProfilePage({ token }: ProfilePageProps) {
  const [profile, setProfile] = useState<UserProfile>({
    first_name: '',
    last_name: '',
    date_of_birth: '',
  });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const { t } = useTranslation();

  // 2FA state
  const [is2FAEnabled, setIs2FAEnabled] = useState(false);
  const [twoFASetup, setTwoFASetup] = useState<TwoFASetup | null>(null);
  const [verifyCode, setVerifyCode] = useState('');
  const [securityMessage, setSecurityMessage] = useState('');
  const [securityError, setSecurityError] = useState('');
  const [securityLoading, setSecurityLoading] = useState(false);

  // Password change state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordMessage, setPasswordMessage] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);

  const newPasswordChecks = useMemo(() => getPasswordChecks(newPassword), [newPassword]);
  const newPasswordStrength = useMemo(() => getStrength(newPasswordChecks), [newPasswordChecks]);

  const fetchProfile = useCallback(async () => {
    setMessage('');
    setError('');
    try {
      const response = await fetch(`${PROFILE_SERVICE_URL}/profiles/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.status === 404) {
        setMessage('No profile found. Create one by saving.');
        setProfile({ first_name: '', last_name: '', date_of_birth: '' });
        return;
      }
      if (!response.ok) {
        throw new Error('Failed to fetch profile');
      }
      const data = await response.json();
      setProfile({
        first_name: data.first_name || '',
        last_name: data.last_name || '',
        date_of_birth: data.date_of_birth || '',
      });
    } catch (err: unknown) {
      const details = err instanceof Error ? err.message : 'Failed to fetch profile';
      setError(details);
    }
  }, [token]);

  const check2FAStatus = useCallback(async () => {
    try {
      const response = await fetch(`${AUTH_SERVICE_URL}/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setIs2FAEnabled(data.totp_enabled === true);
      }
    } catch {
      // Silently fail — status defaults to false
    }
  }, [token]);

  useEffect(() => {
    fetchProfile();
    check2FAStatus();
  }, [fetchProfile, check2FAStatus]);

  const handleProfileChange = (e: ChangeEvent<HTMLInputElement>) => {
    setProfile({ ...profile, [e.target.name]: e.target.value });
  };

  const handleSaveProfile = async (e: FormEvent) => {
    e.preventDefault();
    setMessage('');
    setError('');
    try {
      const response = await fetch(`${PROFILE_SERVICE_URL}/profiles/me`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ ...profile, date_of_birth: profile.date_of_birth || null }),
      });
      if (!response.ok) {
        throw new Error('Failed to save profile');
      }
      setMessage('Profile saved successfully!');
    } catch (err: unknown) {
      const details = err instanceof Error ? err.message : 'Failed to save profile';
      setError(details);
    }
  };

  // 2FA handlers
  const handleEnable2FA = async () => {
    setSecurityMessage('');
    setSecurityError('');
    setSecurityLoading(true);
    try {
      const response = await fetch(`${AUTH_SERVICE_URL}/2fa/setup-json`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error('Failed to start 2FA setup');
      }
      const data: TwoFASetup = await response.json();
      setTwoFASetup(data);
    } catch (err: unknown) {
      const details = err instanceof Error ? err.message : 'Failed to start 2FA setup';
      setSecurityError(details);
    } finally {
      setSecurityLoading(false);
    }
  };

  const handleVerify2FA = async (e: FormEvent) => {
    e.preventDefault();
    setSecurityMessage('');
    setSecurityError('');
    setSecurityLoading(true);
    try {
      const response = await fetch(
        `${API_GATEWAY_URL}/auth/2fa/verify?totp_code=${encodeURIComponent(verifyCode)}`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || 'Invalid code. Please try again.');
      }
      setIs2FAEnabled(true);
      setTwoFASetup(null);
      setVerifyCode('');
      setSecurityMessage('2FA enabled successfully!');
    } catch (err: unknown) {
      const details = err instanceof Error ? err.message : 'Verification failed';
      setSecurityError(details);
    } finally {
      setSecurityLoading(false);
    }
  };

  const handleDisable2FA = async () => {
    setSecurityMessage('');
    setSecurityError('');
    setSecurityLoading(true);
    try {
      const response = await fetch(`${AUTH_SERVICE_URL}/2fa/disable`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error('Failed to disable 2FA');
      }
      setIs2FAEnabled(false);
      setSecurityMessage('2FA has been disabled.');
    } catch (err: unknown) {
      const details = err instanceof Error ? err.message : 'Failed to disable 2FA';
      setSecurityError(details);
    } finally {
      setSecurityLoading(false);
    }
  };

  const handleChangePassword = async (e: FormEvent) => {
    e.preventDefault();
    setPasswordMessage('');
    setPasswordError('');

    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match.');
      return;
    }

    setPasswordLoading(true);
    try {
      const response = await fetch(`${AUTH_SERVICE_URL}/change-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || 'Failed to change password');
      }
      setPasswordMessage('Password changed successfully!');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: unknown) {
      const details = err instanceof Error ? err.message : 'Failed to change password';
      setPasswordError(details);
    } finally {
      setPasswordLoading(false);
    }
  };

  const strengthClass =
    newPasswordStrength === 'strong'
      ? styles.strengthStrong
      : newPasswordStrength === 'medium'
      ? styles.strengthMedium
      : styles.strengthWeak;

  const strengthLabel =
    newPasswordStrength === 'strong'
      ? 'Strong'
      : newPasswordStrength === 'medium'
      ? 'Medium'
      : 'Weak';

  return (
    <div>
      <h1>{t('profile.title')}</h1>
      <p>Fetch and update your profile data from a protected endpoint.</p>
      <div className={styles.subContainer}>
        <form onSubmit={handleSaveProfile}>
          <input
            type="text"
            name="first_name"
            placeholder="First Name"
            value={profile.first_name}
            onChange={handleProfileChange}
            className={styles.input}
          />
          <input
            type="text"
            name="last_name"
            placeholder="Last Name"
            value={profile.last_name}
            onChange={handleProfileChange}
            className={styles.input}
          />
          <input
            type="date"
            name="date_of_birth"
            placeholder="Date of Birth"
            value={profile.date_of_birth}
            onChange={handleProfileChange}
            className={styles.input}
          />
          <button type="submit" className={styles.button}>
            {t('common.save')}
          </button>
        </form>
        {message && <p className={styles.message}>{message}</p>}
        {error && <p className={styles.error}>{error}</p>}
      </div>

      {/* Two-Factor Authentication Section */}
      <div className={`${styles.subContainer} ${styles.securitySection}`}>
        <div className={styles.securityHeader}>
          <h2 style={{ margin: 0, border: 'none', padding: 0 }}>
            {is2FAEnabled ? '🔐' : '🔓'} Two-Factor Authentication
          </h2>
          <span className={`${styles.securityBadge} ${is2FAEnabled ? styles.badgeEnabled : styles.badgeDisabled}`}>
            {is2FAEnabled ? 'Enabled ✓' : 'Disabled'}
          </span>
        </div>

        {is2FAEnabled ? (
          <>
            <p style={{ color: 'var(--lp-text-muted)', margin: '0 0 1rem' }}>
              Your account is protected by two-factor authentication.
            </p>
            <button
              type="button"
              onClick={handleDisable2FA}
              className={styles.dangerButton}
              disabled={securityLoading}
            >
              {securityLoading ? 'Disabling...' : 'Disable 2FA'}
            </button>
          </>
        ) : twoFASetup ? (
          <form onSubmit={handleVerify2FA}>
            <div className={styles.qrContainer}>
              <p style={{ color: 'var(--lp-text-muted)', margin: 0 }}>
                Scan this QR code with your authenticator app
              </p>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(twoFASetup.provisioning_uri)}`}
                alt="QR Code for 2FA setup"
                style={{ borderRadius: 12, background: 'white', padding: 8 }}
                width={200}
                height={200}
              />
              <p style={{ color: 'var(--lp-text-muted)', fontSize: '0.85rem', margin: 0 }}>
                Or enter this key manually:
              </p>
              <code className={styles.secretKey}>{twoFASetup.secret}</code>
            </div>
            <div style={{ marginTop: '1rem' }}>
              <label htmlFor="verify-code">Enter the 6-digit verification code</label>
              <input
                id="verify-code"
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                placeholder="000000"
                value={verifyCode}
                onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                className={`${styles.input} ${styles.totpInput}`}
                style={{ marginTop: '0.5rem' }}
              />
            </div>
            <div className={styles.buttonGroup}>
              <button
                type="button"
                onClick={() => { setTwoFASetup(null); setVerifyCode(''); setSecurityError(''); }}
                className={styles.button}
                style={{ background: 'transparent', border: '1px solid var(--lp-border)', color: 'var(--lp-text-muted)' }}
              >
                Cancel
              </button>
              <button
                type="submit"
                className={styles.button}
                disabled={verifyCode.length !== 6 || securityLoading}
              >
                {securityLoading ? 'Verifying...' : 'Verify & Enable'}
              </button>
            </div>
          </form>
        ) : (
          <>
            <p style={{ color: 'var(--lp-text-muted)', margin: '0 0 1rem' }}>
              Your account is not protected by 2FA.
            </p>
            <button
              type="button"
              onClick={handleEnable2FA}
              className={styles.button}
              disabled={securityLoading}
            >
              {securityLoading ? 'Loading...' : 'Enable 2FA'}
            </button>
          </>
        )}

        {securityMessage && <p className={styles.message} style={{ marginTop: '1rem' }}>{securityMessage}</p>}
        {securityError && <p className={styles.error} style={{ marginTop: '1rem' }}>{securityError}</p>}
      </div>

      {/* Change Password Section */}
      <div className={`${styles.subContainer} ${styles.securitySection}`}>
        <h2>🔑 Change Password</h2>
        <form onSubmit={handleChangePassword}>
          <label htmlFor="current-password">Current Password</label>
          <div className={styles.passwordWrapper}>
            <input
              id="current-password"
              type={showCurrentPassword ? 'text' : 'password'}
              placeholder="Current Password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className={styles.input}
              style={{ paddingRight: '3rem' }}
            />
            <button
              type="button"
              className={styles.passwordToggle}
              onClick={() => setShowCurrentPassword(!showCurrentPassword)}
              aria-label={showCurrentPassword ? 'Hide current password' : 'Show current password'}
            >
              {showCurrentPassword ? '🙈' : '👁️'}
            </button>
          </div>

          <label htmlFor="new-password">New Password</label>
          <div className={styles.passwordWrapper}>
            <input
              id="new-password"
              type={showNewPassword ? 'text' : 'password'}
              placeholder="New Password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className={styles.input}
              style={{ paddingRight: '3rem' }}
            />
            <button
              type="button"
              className={styles.passwordToggle}
              onClick={() => setShowNewPassword(!showNewPassword)}
              aria-label={showNewPassword ? 'Hide new password' : 'Show new password'}
            >
              {showNewPassword ? '🙈' : '👁️'}
            </button>
          </div>

          {newPassword.length > 0 && (
            <>
              <div className={strengthClass} style={{ height: 4, borderRadius: 2, marginTop: '0.5rem', transition: 'all 0.3s' }} />
              <div className={styles.strengthLabel} style={{ color: newPasswordStrength === 'strong' ? '#14b8a6' : newPasswordStrength === 'medium' ? '#d97706' : '#ef4444' }}>
                {strengthLabel}
              </div>
              <ul className={styles.requirements}>
                <li className={newPasswordChecks.length ? styles.requirementMet : styles.requirementUnmet}>
                  {newPasswordChecks.length ? '✓' : '✗'} At least 8 characters
                </li>
                <li className={newPasswordChecks.uppercase ? styles.requirementMet : styles.requirementUnmet}>
                  {newPasswordChecks.uppercase ? '✓' : '✗'} Uppercase letter
                </li>
                <li className={newPasswordChecks.lowercase ? styles.requirementMet : styles.requirementUnmet}>
                  {newPasswordChecks.lowercase ? '✓' : '✗'} Lowercase letter
                </li>
                <li className={newPasswordChecks.digit ? styles.requirementMet : styles.requirementUnmet}>
                  {newPasswordChecks.digit ? '✓' : '✗'} Number
                </li>
                <li className={newPasswordChecks.special ? styles.requirementMet : styles.requirementUnmet}>
                  {newPasswordChecks.special ? '✓' : '✗'} Special character (!@#$%...)
                </li>
              </ul>
            </>
          )}

          <label htmlFor="confirm-password">Confirm Password</label>
          <input
            id="confirm-password"
            type="password"
            placeholder="Confirm New Password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className={styles.input}
          />

          <button
            type="submit"
            className={styles.button}
            disabled={passwordLoading || !currentPassword || !newPassword || !confirmPassword}
          >
            {passwordLoading ? 'Changing...' : 'Change Password'}
          </button>
        </form>
        {passwordMessage && <p className={styles.message} style={{ marginTop: '1rem' }}>{passwordMessage}</p>}
        {passwordError && <p className={styles.error} style={{ marginTop: '1rem' }}>{passwordError}</p>}
      </div>
    </div>
  );
}
