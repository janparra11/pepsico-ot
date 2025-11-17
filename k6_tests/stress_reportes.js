import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 1 },
    { duration: '30s', target: 10 },
    { duration: '30s', target: 30 },
    { duration: '30s', target: 50 },
    { duration: '30s', target: 80 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<5000'], // idealmente << 5000 ms
  },
};

const BASE_URL = 'http://127.0.0.1:8000';

// Si tú usas filtros, puedes ajustar la URL, por ejemplo:
// const REPORTES_URL = `${BASE_URL}/reportes/?rango=ult7`;
const REPORTES_URL = `${BASE_URL}/reportes/`;

export default function () {
  const res = http.get(REPORTES_URL);

  check(res, {
    'status 200 o 302 en /reportes/': (r) =>
      r.status === 200 || r.status === 302,
  });

  sleep(1);
}
