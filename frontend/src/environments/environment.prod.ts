import { basePath } from '../app/core/config/ambiente';

export const environment = {
  production: true,
  // Relativo ao caminho base: "/api/v1" na produção e "/teste/api/v1" no ambiente de teste.
  apiUrl: `${basePath}api/v1`
};
