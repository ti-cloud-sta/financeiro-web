export type AmbienteApi = 'producao' | 'dev';

export const AMBIENTE_API_STORAGE_KEY = 'erp_ambiente_api';

/**
 * Ambiente da API escolhido pelo admin no header (produção ou dev).
 * É lido uma única vez, no carregamento da página: os serviços montam suas URLs
 * a partir de `environment.apiUrl` ao serem criados, por isso trocar de ambiente
 * exige recarregar a aplicação (ver AmbienteApiService).
 */
export function lerAmbienteApi(): AmbienteApi {
  try {
    return localStorage.getItem(AMBIENTE_API_STORAGE_KEY) === 'dev' ? 'dev' : 'producao';
  } catch {
    return 'producao';
  }
}
