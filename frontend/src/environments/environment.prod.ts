import { lerAmbienteApi } from '../app/core/config/ambiente-api';

const ambienteApi = lerAmbienteApi();

export const environment = {
  production: true,
  ambienteApi,
  // Mesmo domínio: o nginx encaminha /api/ para o backend de produção e /api-dev/ para o backend dev.
  apiUrl: ambienteApi === 'dev' ? '/api-dev/v1' : '/api/v1'
};
