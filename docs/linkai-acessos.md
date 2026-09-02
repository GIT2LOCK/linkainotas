# Modelo de acessos internos do LinkAI

O Ariia é usado **somente para autenticação** (e-mail/senha + 2FA). Depois do
login, quem decide o que o usuário vê e faz é o próprio LinkAI, através das
tabelas `linkai_*` no Supabase do LinkAI.

## Migrations

| Migration | Conteúdo |
| --- | --- |
| `20260902162502_*.sql` | Modelo completo: tabelas `linkai_*`, colunas em `usuarios`, escopo de obra nas tabelas operacionais, funções, RLS, matriz de permissões e backfill dos dados existentes. |
| `20260902162557_*.sql` | Endurecimento: `anon` perde `EXECUTE` em todas as funções internas; `authenticated` mantém apenas as funções necessárias. |

Não existe `20260902120000_create_linkai_internal_access.sql` no repositório —
o modelo foi criado nas migrations acima. Correções futuras devem ser
**incrementais** (nova migration), nunca recriando as tabelas.

## Estrutura

```
empresas
  └── linkai_obras            (1 ESCRITORIO ativo + N obras)
        └── linkai_usuario_obras (usuario_id, perfil_codigo, principal, ativo)

linkai_perfis_internos ── linkai_perfil_permissoes ── linkai_permissoes
linkai_user_convites   (pré-cadastro por e-mail)
linkai_activity_logs   (auditoria, somente metadados)
```

- Toda empresa recebe automaticamente a obra `ESCRITORIO` (`tipo = 'escritorio'`),
  criada pelo trigger `linkai_empresas_escritorio` / função `linkai_ensure_escritorio`.
- Índice parcial `linkai_obras_um_escritorio_ativo` garante **um** ESCRITORIO ativo por empresa.
- Índice parcial `linkai_usuario_obras_uma_principal` garante **uma** atribuição principal ativa por usuário.

## Perfis

| Perfil | Escopo | Observações |
| --- | --- | --- |
| `superadmin_2lock` | plataforma | Exclusivo da 2LOCK, todas as permissões, **não** pode ser atribuído a obra (`is_platform_superadmin = true`). |
| `supervisor_empresa` | empresa | Atribuído somente ao ESCRITORIO; vê todas as obras da própria empresa; administra usuários, funções e obras da empresa; nunca acessa outra empresa. |
| `gestor_obra` | obra | Operação completa da obra. |
| `fiscal_obra` | obra | Processa documentos e lança notas. |
| `financeiro_obra` | obra | Notas, planilhas e cadastros. |
| `compras_obra` | obra | Documentos, planilhas e cadastros. |
| `consulta_obra` | obra | Somente leitura. |
| `sem_acesso` | — | Valor de claim para usuário sem atribuição. |

Permissões: `home.view`, `documents.process`, `notes.launch`, `ai.use`,
`spreadsheets.view`, `cloud.view`, `files.view`, `history.view`, `logs.view`,
`queue.monitor`, `access.manage`, `works.manage`, `records.manage`
(matriz em `linkai_perfil_permissoes`; supervisor e superadmin possuem todas).

## Funções

| Função | Quem executa | Papel |
| --- | --- | --- |
| `linkai_assign_user_to_obra(usuario_id, obra_id, perfil_codigo, principal)` | authenticated, service_role | Atribuição atômica: `pg_advisory_xact_lock` por usuário, desativa a principal anterior na mesma transação e valida empresa, usuário ativo, obra ativa, supervisor só no ESCRITORIO, superadmin fora de obra e `access.manage`. |
| `linkai_create_obra(empresa_id, codigo, nome, tipo)` | authenticated, service_role | Exige `works.manage` na própria empresa (ou superadmin). |
| `linkai_link_convite(email)` | service_role | Primeiro acesso: vincula empresa, aplica `two_factor_policy`, cria a atribuição e marca o convite como `linked`. |
| `linkai_log_activity(action, status, payload, message, obra_id, started_at, finished_at)` | authenticated, service_role | Auditoria; remove chaves de conteúdo (`content`, `contentBase64`, `file`, `bytes`) do payload. |
| `linkai_has_permissao`, `linkai_obras_visiveis`, `linkai_can_access_obra`, `linkai_can_manage_empresa`, `linkai_is_supervisor`, `linkai_is_platform_superadmin`, `linkai_current_usuario_id`, `linkai_current_empresa_id`, `linkai_perfil_principal`, `linkai_obra_principal` | authenticated (usadas nas policies), service_role | Helpers de contexto. |
| `linkai_ensure_escritorio`, `linkai_empresa_escritorio_trigger`, `linkai_current_usuario` | service_role | Uso interno. |

`anon` não executa nenhuma delas.

## Claims do token

`custom_access_token_hook` passou a publicar:

```json
{
  "perfil_interno": "supervisor_empresa",
  "permissao": "supervisor_empresa",
  "is_platform_superadmin": false,
  "usuario_id": 4,
  "empresa_id": 2,
  "ativo": true,
  "ariia_user_id": "..."
}
```

`permissao` deixou de refletir o valor legado do Ariia e passa a espelhar o
perfil interno principal (ou `sem_acesso`).

## RLS (resumo)

- `linkai_obras`: SELECT pelas obras visíveis; INSERT/UPDATE apenas com `works.manage` na própria empresa ou superadmin.
- `linkai_usuario_obras`: SELECT das próprias atribuições ou das obras visíveis; escrita apenas por quem administra a empresa da obra.
- `linkai_user_convites`: leitura e escrita apenas por quem administra a empresa.
- `linkai_activity_logs`: o próprio usuário, `access.manage` da empresa, `logs.view` nas obras visíveis e superadmin.
- `pedidos_pendentes`, `notas_processadas`, `robot_logs`: SELECT escopado por obra (`robot_logs` exige `logs.view`); escrita apenas `service_role`.
- Fila do Lumina (`lumina_queue_requests`, `lumina_jobs`, `lumina_queue_logs`): o próprio solicitante, `queue.monitor` nas obras visíveis e superadmin; o worker continua com `service_role` para reservar, renovar, finalizar e registrar logs.
- Catálogos de perfis/permissões: leitura para autenticados, escrita apenas `service_role`.

## Fila do Lumina

`enqueue_lumina_request` agora exige `notes.launch`, preenche `empresa_id` e
`obra_id` a partir da atribuição principal do usuário e registra a atividade
`notes.launch.enqueued`. `lumina_archive_job` propaga `obra_id` para
`lumina_queue_logs`.
