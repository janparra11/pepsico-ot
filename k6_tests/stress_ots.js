import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 1 },   // 1 usuario
    { duration: '30s', target: 10 },  // sube a 10
    { duration: '30s', target: 30 },  // sube a 30
    { duration: '30s', target: 50 },  // sube a 50
    { duration: '30s', target: 80 },  // sube a 80 (pico de estrés)
    { duration: '30s', target: 0 },   // baja a 0 para finalizar
  ],
  thresholds: {
    // No más de 5% de errores
    http_req_failed: ['rate<0.05'],
    // Queremos que el 95% de las peticiones esté bajo 5 segundos
    http_req_duration: ['p(95)<5000'],
  },
};

const BASE_URL = 'http://127.0.0.1:8000';

export default function () {
  const res = http.get(`${BASE_URL}/ots/`);

  check(res, {
    'status 200 o 302 en /ots/': (r) => r.status === 200 || r.status === 302,
  });

  // pequeña pausa para simular un usuario "real"
  sleep(1);
}
