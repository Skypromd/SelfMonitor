import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000/api';

export const options = {
  scenarios: {
    ai_agent_load: {
      executor: 'constant-vus',
      vus: 50,
      duration: '10m',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<3000'],  // AI responses under 3 seconds
    http_req_failed: ['rate<0.02'],     // Error rate under 2%
    errors: ['rate<0.02'],
  },
};

const TEST_TOKEN = 'test-token-for-ai-agent';

const aiQueries = [
  "What's my spending pattern this month?",
  "Help me optimize my budget for next quarter",
  "Show me my tax optimization opportunities",
  "Analyze my income vs expenses trend", 
  "What are my biggest expense categories?",
  "Recommend investment opportunities based on my profile",
  "How can I improve my financial health score?",
  "Create a savings plan for next year",
  "Explain my recent transactions",
  "Generate a financial report summary"
];

export default function () {
  const headers = {
    'Authorization': `Bearer ${TEST_TOKEN}`,
    'Content-Type': 'application/json',
  };
  
  const query = aiQueries[Math.floor(Math.random() * aiQueries.length)];
  
  const payload = JSON.stringify({
    message: query,
    session_id: `load-test-${__VU}-${__ITER}`,
    context: {
      user_id: `test-user-${__VU}`,
      timestamp: new Date().toISOString()
    }
  });
  
  const response = http.post(`${BASE_URL}/ai-agent/chat`, payload, { headers });
  
  check(response, {
    'AI agent response status is 200': (r) => r.status === 200,
    'AI agent response time < 3s': (r) => r.timings.duration < 3000,
    'AI agent response has content': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.response && body.response.length > 0;
      } catch (e) {
        return false;
      }
    },
  }) || errorRate.add(1);
  
  if (response.status !== 200) {
    console.error(`AI Agent failed: ${response.status} ${response.body}`);
  }
  
  sleep(Math.random() * 3 + 2); // Random sleep 2-5 seconds (realistic user behavior)
}