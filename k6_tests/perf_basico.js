import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,              // 10 usuarios concurrentes
  duration: '1m',       // durante 1 minuto
  thresholds: {
    http_req_failed: ['rate<0.01'],     // Máx 1% de errores
    http_req_duration: ['p(95)<2000'],  // 95% de peticiones bajo 2s
  },
};

const BASE_URL = 'http://127.0.0.1:8000';

export default function () {
  // 1) Login
  const resLogin = http.get(`${BASE_URL}/login/`);
  check(resLogin, {
    'login responde 200/302': (r) => r.status === 200 || r.status === 302,
  });

  // 2) Inicio
  const resHome = http.get(`${BASE_URL}/`);
  check(resHome, {
    'home responde 200/302': (r) => r.status === 200 || r.status === 302,
  });

  // 3) Lista de OTs
  const resOTs = http.get(`${BASE_URL}/ots/`);
  check(resOTs, {
    'ots responde 200/302': (r) => r.status === 200 || r.status === 302,
  });

  // 4) Reportes (dashboard)
  const resReportes = http.get(`${BASE_URL}/reportes/`);
  check(resReportes, {
    'reportes responde 200/302': (r) => r.status === 200 || r.status === 302,
  });

  // Pausa de 1 segundo entre iteraciones de usuario
  sleep(1);
}
