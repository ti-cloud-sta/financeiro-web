/**
 * Produção e teste usam o mesmo código; o que diferencia é o caminho base do build (<base href>):
 *   https://stamaria.cloud/        → produção (base "/")
 *   https://stamaria.cloud/teste/  → teste    (base "/teste/", build com --base-href /teste/)
 */
export const basePath = new URL(document.baseURI).pathname;

export const isAmbienteTeste = basePath.startsWith('/teste/');

/**
 * Os dois ambientes ficam no mesmo domínio e compartilham o localStorage/sessionStorage.
 * Chaves de sessão ganham prefixo no teste para que logar em um não derrube o outro.
 */
export function chaveStorage(nome: string): string {
  return isAmbienteTeste ? `teste_${nome}` : nome;
}
