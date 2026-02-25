import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000/api';

export const options = {
  stages: [
    { duration: '2m', target: 100 },   // Ramp up to 100 users
    { duration: '5m', target: 100 },   // Stay at 100 users
    { duration: '2m', target: 200 },   // Ramp up to 200 users  
    { duration: '5m', target: 200 },   // Stay at 200 users
    { duration: '2m', target: 0 },     // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],   // 95% of requests under 500ms
    http_req_failed: ['rate<0.01'],     // Error rate under 1%
    errors: ['rate<0.01'],
  },
};

export default function () {
  // User registration flow
  let registerPayload = JSON.stringify({
    email: `testuser${Math.random()}@example.com`,
    password: 'SecurePass123!',
    name: 'Load Test User'
  });
  
  let registerRes = http.post(`${BASE_URL}/auth/register`, registerPayload, {
    headers: { 'Content-Type': 'application/json' },
  });
  
  check(registerRes, {
    'registration status is 201': (r) => r.status === 201,
    'registration response time < 500ms': (r) => r.timings.duration < 500,
  }) || errorRate.add(1);
  
  if (registerRes.status !== 201) {
    console.error(`Registration failed: ${registerRes.status} ${registerRes.body}`);
    return;
  }
  
  sleep(1);
  
  // User login flow
  let loginPayload = `username=${encodeURIComponent(JSON.parse(registerPayload).email)}&password=${encodeURIComponent(JSON.parse(registerPayload).password)}`;
  
  let loginRes = http.post(`${BASE_URL}/auth/token`, loginPayload, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  
  check(loginRes, {
    'login status is 200': (r) => r.status === 200,
    'login response time < 200ms': (r) => r.timings.duration < 200,
    'token received': (r) => JSON.parse(r.body).access_token !== undefined,
  }) || errorRate.add(1);
  
  if (loginRes.status !== 200) {
    console.error(`Login failed: ${loginRes.status} ${loginRes.body}`);
    return;
  }
  
  const token = JSON.parse(loginRes.body).access_token;
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  
  sleep(1);
  
  // User profile operations
  let profileRes = http.get(`${BASE_URL}/user-profile/me`, { headers });
  
  check(profileRes, {
    'profile fetch status is 200': (r) => r.status === 200,
    'profile response time < 300ms': (r) => r.timings.duration < 300,
  }) || errorRate.add(1);
  
  sleep(1);
  
  // Transaction operations
  let transactionPayload = JSON.stringify({
    amount: Math.floor(Math.random() * 1000) + 10,
    description: `Load test transaction ${Math.random()}`,
    category: 'testing',
    date: new Date().toISOString().split('T')[0]
  });
  
  let transactionRes = http.post(`${BASE_URL}/transactions/`, transactionPayload, { headers });
  
  check(transactionRes, {
    'transaction creation status is 201': (r) => r.status === 201,
    'transaction response time < 400ms': (r) => r.timings.duration < 400,
  }) || errorRate.add(1);
  
  sleep(1);
  
  // Analytics fetch
  let analyticsRes = http.get(`${BASE_URL}/analytics/dashboard`, { headers });
  
  check(analyticsRes, {
    'analytics fetch status is 200': (r) => r.status === 200,
    'analytics response time < 600ms': (r) => r.timings.duration < 600,
  }) || errorRate.add(1);
  
  sleep(Math.random() * 2 + 1); // Random sleep between 1-3 seconds
}