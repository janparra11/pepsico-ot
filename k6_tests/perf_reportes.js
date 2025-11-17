import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,              // 10 usuarios concurrentes
  duration: '1m',       // durante 1 minuto
  thresholds: {
    http_req_failed: ['rate<0.01'],      // Máx 1% errores
    http_req_duration: ['p(95)<2000'],   // 95% de peticiones bajo 2s
  },
};

const BASE_URL = 'http://127.0.0.1:8000';

export default function () {
  const res = http.get(`${BASE_URL}/reportes/?rango=ult7`);

  check(res, {
    'reportes ult7 responde 200/302': (r) => r.status === 200 || r.status === 302,
  });

  sleep(1);
}
