import { lerAmbienteApi } from '../app/core/config/ambiente-api';

const ambienteApi = lerAmbienteApi();

export const environment = {
  production: false,
  ambienteApi,
  // Local: "produção" é o backend rodando na máquina; "dev" é a API dev da VPS (banco stamariabd_dev).
  apiUrl: ambienteApi === 'dev' ? 'https://stamaria.cloud/api-dev/v1' : 'http://127.0.0.1:8000/api/v1'
};
