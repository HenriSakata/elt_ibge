# [Desafio Técnico] ETL de arrecadação municipal — API pública → PostgreSQL

/label ~"desafio-tecnico" ~"estagio-ti" ~"python" ~"postgresql" ~"integracao"
/estimate 4h

---

## Contexto

A Tributech trabalha com modernização fiscal e cadastral de municípios. Boa parte do diagnóstico de um projeto começa com a mesma pergunta: **quanto esse município arrecada de IPTU e ISS, e como isso se compara com municípios parecidos?**

Esse dado é público. O Tesouro Nacional expõe pela API do SICONFI as declarações contábeis de todos os entes da federação, e o IBGE expõe a lista de municípios e população.

Este desafio é montar o pipeline que transforma essas duas APIs em uma base consultável.

## Objetivo

Construir uma aplicação ETL que consome APIs públicas, trata os dados e os carrega em PostgreSQL de forma **idempotente**, com log de execução e uma camada de consulta em cima.

**Não é teste de velocidade.** Uso de IA é liberado e esperado. O que será avaliado é se você consegue **explicar e defender** cada decisão.

## Fontes

| Fonte | Uso | Auth |
|---|---|---|
| [SICONFI](http://apidatalake.tesouro.gov.br/docs/siconfi/) (Tesouro Nacional) | Receita declarada por município e exercício (DCA - Anexo I-C) | Não |
| [IBGE Localidades](https://servicodados.ibge.gov.br/api/docs/localidades) | Municípios do PR e códigos IBGE | Não |
| [IBGE Agregados/SIDRA](https://servicodados.ibge.gov.br/api/docs/agregados) | População estimada (para cálculo per capita) | Não |

> A API do SICONFI já teve períodos de indisponibilidade. Salvar o payload bruto em disco na primeira execução resolve — e é boa prática de ETL de qualquer forma.

## Stack

Python 3.11+ · `httpx` ou `requests` · `psycopg` · PostgreSQL no [Neon](https://neon.tech) ou [Supabase](https://supabase.com) (free tier, sem Docker) · `fastapi` na última etapa

---

## Escopo

### Etapa 0 — Setup (~30 min)

- [x] Instância PostgreSQL na nuvem
- [ ] Repositório Git com `requirements.txt` e `.env.example` (**sem** credenciais commitadas)
- [X] Explorar as APIs no navegador/Postman **antes** de escrever código — entender o formato de resposta é metade do trabalho

### Etapa 1 — Extract (~1h15) ⭐ núcleo do desafio

- [X] Buscar os municípios do Paraná na API do IBGE
- [ ] Para cada município, buscar as receitas no SICONFI (sugestão: exercícios 2021–2023, para ter série histórica)
- [ ] Salvar o **payload bruto** em `data/raw/` antes de qualquer tratamento
- [ ] Tratar corretamente:
  - **Paginação** — o SICONFI retorna 5.000 itens por página por padrão
  - **Timeout** explícito em toda requisição
  - **Retry com backoff** em erro 5xx e timeout
  - **Rate limit** — um `sleep` entre chamadas, para não derrubar (nem ser bloqueado por) um serviço público
  - **Falha parcial** — se o município 200 falhar, os 199 anteriores não podem ser perdidos

> Nunca deixe um `except: pass` no código. Cada falha precisa ir para o log com o motivo.

### Etapa 2 — Transform + Load (~1h15)

- [ ] Tabela `staging_raw` guardando a resposta em `JSONB` + timestamp de coleta
- [ ] Tabelas finais: `municipio`, `exercicio_receita` (código IBGE, exercício, conta, valor)
- [ ] Carga **idempotente** — rodar o script duas vezes não pode duplicar nada (`ON CONFLICT ... DO UPDATE`)
- [ ] Tabela `etl_execucao` registrando: início, fim, status, registros lidos, gravados e rejeitados
- [ ] Tratar as inconsistências reais que vão aparecer:
  - Município que não declarou em determinado exercício
  - Valores nulos ou zerados
  - Nomenclatura de conta que muda entre exercícios
  - Código IBGE de 7 dígitos vs. código com dígito verificador

### Etapa 3 — Camada de consulta (~1h)

- [ ] Queries SQL respondendo:
  - Ranking de arrecadação de IPTU **per capita** dos municípios do PR
  - Evolução ano a ano de IPTU e ISS de um município específico
  - Municípios que tiveram **queda** de arrecadação de IPTU no período
  - Municípios que não declararam em algum exercício (cobertura da base)
- [ ] API FastAPI com duas rotas:
  - `GET /municipios/{codigo_ibge}/receitas`
  - `GET /ranking/iptu-per-capita?uf=PR&exercicio=2023`

---

## Definition of Done

- [ ] `README.md` com: como rodar, decisões tomadas, e o resultado do ranking (pode ser print da tabela)
- [ ] Seção **"Próximos passos"** com o que ficou de fora e como você faria
- [ ] Nenhuma credencial no repositório
- [ ] Rodar o ETL duas vezes seguidas produz o mesmo estado final do banco
- [ ] Você responde às perguntas de defesa abaixo sem consultar o código

## Perguntas de defesa

Se travar em alguma, invista o tempo restante em entender o que já fez — **não** em adicionar funcionalidade.

1. O que acontece se o ETL for executado duas vezes? E se cair no meio da execução?
2. Por que salvar o payload bruto antes de tratar?
3. Por que `NUMERIC` e não `FLOAT` para valores monetários?
4. A API voltou 429 ou 503. O que seu código faz? E o que **deveria** fazer?
5. Um município aparece com IPTU zerado. É erro do ETL, falha da fonte, ou o município realmente não arrecadou? Como você investigaria?
6. Amanhã precisa rodar isso para os 5.570 municípios do Brasil, todo mês. O que muda?

## Fora de escopo

Documentar no README como evolução futura, sem implementar:

- Agendamento (cron / Airflow / GitHub Actions)
- Carga incremental por data de última alteração
- Dashboard ou visualização geográfica dos municípios
- Testes automatizados do parser
- Alertas de falha de execução

## Dicas

- Explore a API no navegador antes de codar. Entender o payload economiza horas.
- Mantenha um `DECISOES.md` curto anotando cada escolha **enquanto** trabalha. Depois você não lembra.
- Ao usar IA: peça o código, depois peça para ela **te questionar** sobre ele. É o melhor ensaio para a conversa.
- Se a fonte estiver fora do ar no dia: use o cache bruto, documente no README e siga. Lidar com fonte indisponível faz parte do trabalho.
