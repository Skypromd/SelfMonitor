import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { getToken, setToken as storeToken, removeToken } from '../api';

type User = {
  email: string;
  is_admin: boolean;
};

type AuthContextType = {
  token: string | null;
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<string>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType>({} as AuthContextType);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const stored = await getToken();
      if (stored) {
        setTokenState(stored);
        decodeUser(stored);
      }
      setLoading(false);
    })();
  }, []);

  function decodeUser(t: string) {
    try {
      const payload = JSON.parse(atob(t.split('.')[1]));
      setUser({ email: payload.sub || '', is_admin: false });
    } catch {
      setUser({ email: '', is_admin: false });
    }
  }

  async function login(email: string, password: string) {
    const params = new URLSearchParams();
    params.append('username', email);
    params.append('password', password);
    const res = await fetch(`http://10.0.2.2:8000/api/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: params.toString(),
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || 'Login failed');
    }
    const data = await res.json();
    await storeToken(data.access_token);
    setTokenState(data.access_token);
    decodeUser(data.access_token);
  }

  async function register(email: string, password: string): Promise<string> {
    const res = await fetch(`http://10.0.2.2:8000/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || 'Registration failed');
    }
    const data = await res.json();
    return data.email;
  }

  async function logout() {
    await removeToken();
    setTokenState(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ token, user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
