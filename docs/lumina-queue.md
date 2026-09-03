# Fila distribuída do Lumina

O lançamento de notas usa uma fila durável no Supabase:

- `public.lumina_queue_requests` — solicitação-pai, com `queue_number` único e crescente (`public.lumina_queue_number_seq`), totais e situação.
- `public.lumina_jobs` — itens ativos da fila (um ou mais por solicitação), com `queue_request_id` e `item_number`.
- `public.lumina_queue_logs` — histórico permanente dos itens finalizados.

O usuário apenas cria a solicitação; cada máquina Windows executa um worker que reserva atomicamente o próximo item disponível. Não é necessário escolher IP ou porta.

## 1. Banco

Migrações aplicadas, nesta ordem:

1. `supabase/migrations/20260819130000_create_lumina_jobs_queue.sql`
2. `supabase/migrations/20260827161250_*.sql` (fila durável, logs, RPCs e RLS)
3. `supabase/migrations/20260827161322_*.sql` (restrição de execução das funções internas)
4. `supabase/migrations/20260903120000_add_lumina_credentials_and_profile.sql` (credenciais cifradas e fotos de perfil)

### Funções

- `enqueue_lumina_request(p_action, p_payload, p_items)` — cria solicitação + itens na mesma transação (máx. 1000 itens); exige usuário autenticado e ativo. Executável por `authenticated` e `service_role`.
- `claim_lumina_job(p_worker_id, p_lease_seconds)` — reserva atômica (`FOR UPDATE SKIP LOCKED` + lock por usuário). Um item por usuário em execução; usuários diferentes rodam em paralelo. Itens com 3 tentativas viram `failed` e vão para o log.
- `renew_lumina_job(p_job_id, p_worker_id, p_lease_seconds)` — renova `leased_until`/`heartbeat_at`.
- `release_lumina_job(p_job_id, p_worker_id, p_message)` — devolve o item para `queued`.
- `finish_lumina_job(p_job_id, p_worker_id, p_status, p_message)` — grava o log, atualiza os contadores da solicitação-pai e remove o item da fila, tudo na mesma transação.

Os quatro RPCs operacionais são executáveis somente por `service_role` (chave usada apenas pelos workers, nunca no frontend).

## 2. Variáveis em cada máquina Windows

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_SERVICE_ROLE_KEY=chave-de-servico
LINKAI_LUMINA_CREDENTIALS_KEY=mesmo-segredo-do-Lovable
LINKAI_WORKER_ID=lumina-maquina-01
LINKAI_QUEUE_WORKER_ENABLED=true
LINKAI_QUEUE_POLL_SECONDS=3
LINKAI_QUEUE_LEASE_SECONDS=300
LUMINA_EXECUTABLE_PATH=C:\caminho\para\900_Lumina.exe
```

Na segunda máquina troque apenas `LINKAI_WORKER_ID=lumina-maquina-02`.

## 3. Iniciar o worker

```powershell
cd C:\LinkAI
.\lumina_bot\.venv\Scripts\python.exe -m uvicorn backend.api.server:app --host 0.0.0.0 --port 8766
curl.exe http://127.0.0.1:8766/health
```

## 4. Fluxo

1. O usuário clica em **Iniciar lançamento**; a aplicação chama `enqueue_lumina_request`.
2. A solicitação recebe um número e nasce com itens `queued`.
3. A primeira máquina livre executa `claim_lumina_job` e o item vira `running`.
4. Enquanto o Lumina estiver aberto, o worker renova a reserva.
5. Ao concluir, `finish_lumina_job` grava o histórico, atualiza a solicitação-pai e remove o item da fila.
6. Se uma máquina cair, o item volta a ficar elegível após `leased_until` expirar, com limite de 3 tentativas.

`LINKAI_LUMINA_CREDENTIALS_KEY` deve ser exatamente igual no ambiente seguro
do Lovable e nas duas máquinas. Ela protege a senha Lumina individual de cada
usuário. Nunca coloque esse valor no frontend, em uma variável `VITE_*` ou no
Git. O usuário cadastra seu login Lumina na primeira utilização de **Iniciar
lançamento**; depois, o estado fica disponível em **Meu Perfil**. A troca
posterior é encaminhada ao suporte técnico pelo botão **Alterar login Lumina**.
