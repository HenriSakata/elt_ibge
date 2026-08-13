# Etapa 1 — Extract (~1h15) ⭐ núcleo do desafio
# [ ] Buscar os municípios do Paraná na API do IBGE
# [ ] Para cada município, buscar as receitas no SICONFI (sugestão: exercícios 2021–2023, para ter série histórica)
# [ ] Salvar o payload bruto em data/raw/ antes de qualquer tratamento
# [ ] Tratar corretamente:
    # Paginação — o SICONFI retorna 5.000 itens por página por padrão
    # Timeout explícito em toda requisição
    # Retry com backoff em erro 5xx e timeout
    # Rate limit — um sleep entre chamadas, para não derrubar (nem ser bloqueado por) um serviço público
    # Falha parcial — se o município 200 falhar, os 199 anteriores não podem ser perdidos
    # Nunca deixe um except: pass no código. Cada falha precisa ir para o log com o motivo.

#IMPORTAR AS DEPENDÊNCIAS
import os
import json
import logging
import asyncio
import requests
from pathlib import Path
from requests.exceptions import RequestException, Timeout

#Configuracão do logging
logging.basicConfig(
   level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("extract.log"),
        logging.StreamHandler()
    ]
)

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

async def buscar_municipios_pr():
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/41/municipios"
    logging.info("Buscando municípios do Paraná na API do IBGE...")

    try:
        response = await asyncio.to_thread(requests.get, url, timeout=10.0)
        response.raise_for_status()
        municipios = response.json()
        logging.info(f"Sucesso! {len(municipios)} municípios encontrados.")

        # test_extract_id = []
        # for i in municipios:
        #     id_mun = i["id"],i["nome"]
        #     test_extract_id.append(id_mun)

        return municipios
    except RequestException as e:
        logging.error(f"Erro crítico ao buscar municípios do IBGE: {e}")
        raise

# Buscar receitas, tratar paginação, timeout e retry assíncrono
async def buscar_receitas_siconfi(cod_ibge, exercicio, semaphore):
    # Endpoit da API do SICONFI
    url = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/dca"
    # Limite de itens por página
    limit = 5000
    # Offset inicial
    offset = 0
    # lista para armazenar as corrotinas de cada municipio e ano
    todos_itens = []

    # Loop principal
    while True:

        # Declaração de parametrôs para a requisição
        params = {
            "an_exercicio": 2021,
            "id_ente": 4106902,
            "no_anexo": "DCA-Anexo I-C",
            "limit": limit,
            "offset": offset
        }
        # Variaveis de controle de paginação
        tentativas = 3
        sucesso = False
        dados_pagina = None
        # Loop para fazer a requisição (Retry)
        for tentativa in range(tentativas):
            # Bloco de exceção para tratar erros de requisição (try/except)
            try:
                # Limitar o número de requisições simultâneas com o semáforo (5)
                async with semaphore:
                    response = await asyncio.to_thread(requests.get, url, params=params, timeout=10.0)
                # Backoff exponencial para retry em caso de erro 5xx ou timeout
                if response.status_code in (429, 500, 502, 503, 504):
                    tempo_espera = 2**tentativa
                    logging.warning(f"[{cod_ibge}-{exercicio}] Erro {response.status_code}. Retry {tentativa + 1}/{tentativas}. Esperando {tempo_espera}s.")
                    # Async sleep: Pausa apenas essa corrotina.
                    await asyncio.sleep(tempo_espera)
                    continue
                # Abrir exceção para qualquer outro erro de requisição
                response.raise_for_status()
                # Se a requisição for bem-sucedida, salvar os dados da página e sair do loop de retry
                dados_pagina = response.json()
                # Se a requisição for bem-sucedida, salvar os dados da página e sair do loop de retry
                sucesso = True
                break
            # Retry com backoff para exceções
            except (RequestException, Timeout) as e:
                tempo_espera = 2 ** tentativa
                logging.warning(f"[{cod_ibge}-{exercicio}] Rede/Timeout: {e}. Retry {tentativa + 1} / {tentativas}. Esperando {tempo_espera}s.")
                await asyncio.sleep(tempo_espera)
        # Informar falha definitiva que não foi resolvida com retry
        if not sucesso:
            logging.error(f"[{cod_ibge}-{exercicio}] Falha definitiva.")
            return {"erro": "Falha na comunicação", "items": []}
        # Puxar os itens da lista 
        itens = dados_pagina.get("items", [])
        # Adicionar a lista "todos_itens"
        todos_itens.extend(itens)
        # Paginação SICONFI
        if not dados_pagina.get("hasMore", False):
            break
        # Pular o valor de limit para a proxima leva de dados do mesmo municio e exercicio
        offset += limit
    # Retornar a minha lista com todos os itens para salvar em json
    return {"items": todos_itens}
        

# Processar, criar e salvar arquivo JSON para cada municipio e ano
async def processar_municipio_ano(cod_ibge, exercicio, semaphore, nome):
    # Arquivo JSON de saída para cada município e ano
    arquivo_saida = RAW_DIR / f"{cod_ibge}_{exercicio}.json"
    # Falha parcial - se o municipios ja exists()
    if arquivo_saida.exists():
        logging.info(f"Arquivo {arquivo_saida} já existe. Pulando download.")
        return
    # Loggind informando download do payload bruto
    logging.info(f"Download: {nome} ({cod_ibge}) - Ano: {exercicio}.")
    # Chamar a funcao buscar_receitas_siconfi() para o id do municipio e ano
    resultado = await buscar_receitas_siconfi(cod_ibge, exercicio, semaphore)
    # Salvar o payload bruto em data/raw/ antes de qualquer tratamento com blocos de exceção e logging e erro
    try:
        with open(arquivo_saida, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logging.error(f"Erro ao salvar arquivo para [{nome}-{exercicio}]: {e}")
    # Rate limit - sleep entre chamadas para não derrubar a API (1s)
    await asyncio.sleep(1)

# Funcao principal para orquestrar a extração de dados
async def ruyn_etl_extract_async():
    # Anos de pesquisa sugeridos
    anos_pesquisas = [2021, 2022, 2023]
    # Chamar a função buscar_municipios_pr()
    municipios = await buscar_municipios_pr()
    # Logging informando o total de municípios a processar
    logging.info(f"Total de municípios a processar: {len(municipios)}")
    # Limite de concorrência para não sobrecarregar a API
    semaphore = asyncio.Semaphore(5)  
    # Lista de tarefas para processar
    tasks = [] 
    # Loop para processar cada município e ano
    for municipio in municipios:
        nome_municipio = municipio["nome"]
        id_municipio = municipio["id"]
        logging.info(f"Processando município: {id_municipio}, {nome_municipio}")
        for ano in anos_pesquisas:
            logging.info(f"Processando ano: {ano} para município: {id_municipio}")
            task = processar_municipio_ano(id_municipio, ano, semaphore, nome_municipio)
            tasks.append(task)
    # Executar todas as tarefas de forma assíncrona e concorrente
    await asyncio.gather(*tasks)

    logging.info("Etapa 1 (Extract) concluída com sucesso!")


if __name__ == "__main__":
    # Event Loop
    test = asyncio.run(ruyn_etl_extract_async())
    print(test)

