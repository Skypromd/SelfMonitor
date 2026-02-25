import http from 'k6/http';
import { check } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000/api';

export const options = {
  scenarios: {
    stress_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 100 },    // Ramp up to 100 VUs
        { duration: '2m', target: 500 },    // Ramp up to 500 VUs
        { duration: '3m', target: 1000 },   // Ramp up to 1000 VUs
        { duration: '2m', target: 1500 },   // Spike to 1500 VUs
        { duration: '1m', target: 0 },      // Ramp down
      ],
      gracefulRampDown: '30s',
    },
  },
  thresholds: {
    http_req_duration: [
      'p(50)<200',     // 50% under 200ms
      'p(95)<800',     // 95% under 800ms (stress conditions)
      'p(99)<1500',    // 99% under 1.5s
    ],
    http_req_failed: ['rate<0.05'],  // Error rate under 5% (stress tolerance)
    errors: ['rate<0.05'],
  },
};

// Pre-created test token for stress testing
const TEST_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test';

export default function () {
  const headers = {
    'Authorization': `Bearer ${TEST_TOKEN}`,
    'Content-Type': 'application/json',
  };
  
  // Weighted API endpoint testing
  const endpoints = [
    { url: '/auth/health', weight: 10, method: 'GET' },
    { url: '/user-profile/health', weight: 8, method: 'GET' },
    { url: '/transactions/health', weight: 15, method: 'GET' },
    { url: '/analytics/health', weight: 12, method: 'GET' },
    { url: '/ai-agent/health', weight: 5, method: 'GET' },
    { url: '/fraud-detection/health', weight: 8, method: 'GET' },
  ];
  
  // Select random endpoint based on weights
  const totalWeight = endpoints.reduce((sum, endpoint) => sum + endpoint.weight, 0);
  let random = Math.random() * totalWeight;
  let selectedEndpoint = endpoints[0];
  
  for (const endpoint of endpoints) {
    if (random <= endpoint.weight) {
      selectedEndpoint = endpoint;
      break;
    }
    random -= endpoint.weight;
  }
  
  let response;
  
  if (selectedEndpoint.method === 'GET') {
    response = http.get(`${BASE_URL}${selectedEndpoint.url}`, { headers });
  } else {
    response = http.post(`${BASE_URL}${selectedEndpoint.url}`, '{}', { headers });
  }
  
  const result = check(response, {
    'status is 200': (r) => r.status === 200,
    'response time acceptable': (r) => r.timings.duration < 1000,
  });
  
  if (!result) {
    errorRate.add(1);
    console.error(`Failed request to ${selectedEndpoint.url}: ${response.status}`);
  }
}