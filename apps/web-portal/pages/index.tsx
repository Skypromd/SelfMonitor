import { useState, type FormEvent } from 'react';
import styles from '../styles/Home.module.css';

const AUTH_SERVICE_BASE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8000';

type LoginPageProps = {
  onLoginSuccess?: (token: string, email?: string) => void;
};

export default function HomePage({ onLoginSuccess }: LoginPageProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const clearMessages = () => {
    setMessage('');
    setError('');
  };

  const handleRegister = async (event: FormEvent) => {
    event.preventDefault();
    clearMessages();
    setIsLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await fetch(`${AUTH_SERVICE_BASE_URL}/register`, {
        body: formData,
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        method: 'POST',
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Registration failed');
      }

      setMessage(`User ${data.email} registered successfully. You can now log in.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogin = async (event: FormEvent) => {
    event.preventDefault();
    clearMessages();
    setIsLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await fetch(`${AUTH_SERVICE_BASE_URL}/token`, {
        body: formData,
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        method: 'POST',
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Login failed');
      }

      if (onLoginSuccess) {
        onLoginSuccess(data.access_token, email);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <main className={styles.main}>
        <h1 className={styles.title}>Welcome!</h1>
        <p className={styles.description}>Register or log in to continue</p>

        <div className={styles.formContainer}>
          <form>
            <input
              className={styles.input}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="Email"
              type="email"
              value={email}
            />
            <input
              className={styles.input}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Password"
              type="password"
              value={password}
            />
            <div className={styles.buttonGroup}>
              <button className={styles.button} disabled={isLoading} onClick={handleRegister}>
                Register
              </button>
              <button className={styles.button} disabled={isLoading} onClick={handleLogin}>
                Login
              </button>
            </div>
          </form>
        </div>

        {message && <p className={styles.message}>{message}</p>}
        {error && <p className={styles.error}>{error}</p>}
      </main>
    </div>
  );
}
