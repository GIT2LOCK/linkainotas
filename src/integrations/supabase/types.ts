export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      empresas: {
        Row: {
          cnpj: string | null
          criado_em: string | null
          id: number
          nome_fantasia: string
          razao_social: string | null
        }
        Insert: {
          cnpj?: string | null
          criado_em?: string | null
          id?: number
          nome_fantasia: string
          razao_social?: string | null
        }
        Update: {
          cnpj?: string | null
          criado_em?: string | null
          id?: number
          nome_fantasia?: string
          razao_social?: string | null
        }
        Relationships: []
      }
      indicadores_construcao: {
        Row: {
          codigo: string
          data_atualizacao: string
          data_referencia: string
          fonte: string | null
          id: string
          nome: string
          unidade: string | null
          valor: number
        }
        Insert: {
          codigo: string
          data_atualizacao?: string
          data_referencia: string
          fonte?: string | null
          id?: string
          nome: string
          unidade?: string | null
          valor: number
        }
        Update: {
          codigo?: string
          data_atualizacao?: string
          data_referencia?: string
          fonte?: string | null
          id?: string
          nome?: string
          unidade?: string | null
          valor?: number
        }
        Relationships: []
      }
      indicadores_historico: {
        Row: {
          codigo: string
          created_at: string
          data_referencia: string
          id: string
          valor: number
        }
        Insert: {
          codigo: string
          created_at?: string
          data_referencia: string
          id?: string
          valor: number
        }
        Update: {
          codigo?: string
          created_at?: string
          data_referencia?: string
          id?: string
          valor?: number
        }
        Relationships: []
      }
      linkai_activity_logs: {
        Row: {
          action: string
          actor_user_id: string | null
          actor_usuario_id: number | null
          created_at: string
          empresa_id: number | null
          finished_at: string | null
          id: string
          message: string | null
          obra_id: string | null
          payload: Json
          started_at: string | null
          status: string
        }
        Insert: {
          action: string
          actor_user_id?: string | null
          actor_usuario_id?: number | null
          created_at?: string
          empresa_id?: number | null
          finished_at?: string | null
          id?: string
          message?: string | null
          obra_id?: string | null
          payload?: Json
          started_at?: string | null
          status?: string
        }
        Update: {
          action?: string
          actor_user_id?: string | null
          actor_usuario_id?: number | null
          created_at?: string
          empresa_id?: number | null
          finished_at?: string | null
          id?: string
          message?: string | null
          obra_id?: string | null
          payload?: Json
          started_at?: string | null
          status?: string
        }
        Relationships: [
          {
            foreignKeyName: "linkai_activity_logs_actor_usuario_id_fkey"
            columns: ["actor_usuario_id"]
            isOneToOne: false
            referencedRelation: "usuarios"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "linkai_activity_logs_empresa_id_fkey"
            columns: ["empresa_id"]
            isOneToOne: false
            referencedRelation: "empresas"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "linkai_activity_logs_obra_id_fkey"
            columns: ["obra_id"]
            isOneToOne: false
            referencedRelation: "linkai_obras"
            referencedColumns: ["id"]
          },
        ]
      }
      linkai_convite_obras: {
        Row: {
          convite_id: string
          created_at: string
          obra_id: string
          perfil_codigo: string
          principal: boolean
        }
        Insert: {
          convite_id: string
          created_at?: string
          obra_id: string
          perfil_codigo: string
          principal?: boolean
        }
        Update: {
          convite_id?: string
          created_at?: string
          obra_id?: string
          perfil_codigo?: string
          principal?: boolean
        }
        Relationships: [
          {
            foreignKeyName: "linkai_convite_obras_convite_id_fkey"
            columns: ["convite_id"]
            isOneToOne: false
            referencedRelation: "linkai_user_convites"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "linkai_convite_obras_obra_id_fkey"
            columns: ["obra_id"]
            isOneToOne: false
            referencedRelation: "linkai_obras"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "linkai_convite_obras_perfil_codigo_fkey"
            columns: ["perfil_codigo"]
            isOneToOne: false
            referencedRelation: "linkai_perfis_internos"
            referencedColumns: ["codigo"]
          },
        ]
      }
      linkai_convite_permissoes: {
        Row: {
          concedida: boolean
          convite_id: string
          created_at: string
          permissao_codigo: string
        }
        Insert: {
          concedida?: boolean
          convite_id: string
          created_at?: string
          permissao_codigo: string
        }
        Update: {
          concedida?: boolean
          convite_id?: string
          created_at?: string
          permissao_codigo?: string
        }
        Relationships: [
          {
            foreignKeyName: "linkai_convite_permissoes_convite_id_fkey"
            columns: ["convite_id"]
            isOneToOne: false
            referencedRelation: "linkai_user_convites"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "linkai_convite_permissoes_permissao_codigo_fkey"
            columns: ["permissao_codigo"]
            isOneToOne: false
            referencedRelation: "linkai_permissoes"
            referencedColumns: ["codigo"]
          },
        ]
      }
      linkai_obras: {
        Row: {
          ativo: boolean
          codigo: string
          created_at: string
          empresa_id: number
          id: string
          nome: string
          tipo: string
          updated_at: string
        }
        Insert: {
          ativo?: boolean
          codigo: string
          created_at?: string
          empresa_id: number
          id?: string
          nome: string
          tipo?: string
          updated_at?: string
        }
        Update: {
          ativo?: boolean
          codigo?: string
          created_at?: string
          empresa_id?: number
          id?: string
          nome?: string
          tipo?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "linkai_obras_empresa_id_fkey"
            columns: ["empresa_id"]
            isOneToOne: false
            referencedRelation: "empresas"
            referencedColumns: ["id"]
          },
        ]
      }
      linkai_perfil_permissoes: {
        Row: {
          created_at: string
          perfil_codigo: string
          permissao_codigo: string
        }
        Insert: {
          created_at?: string
          perfil_codigo: string
          permissao_codigo: string
        }
        Update: {
          created_at?: string
          perfil_codigo?: string
          permissao_codigo?: string
        }
        Relationships: [
          {
            foreignKeyName: "linkai_perfil_permissoes_perfil_codigo_fkey"
            columns: ["perfil_codigo"]
            isOneToOne: false
            referencedRelation: "linkai_perfis_internos"
            referencedColumns: ["codigo"]
          },
          {
            foreignKeyName: "linkai_perfil_permissoes_permissao_codigo_fkey"
            columns: ["permissao_codigo"]
            isOneToOne: false
            referencedRelation: "linkai_permissoes"
            referencedColumns: ["codigo"]
          },
        ]
      }
      linkai_perfis_internos: {
        Row: {
          ativo: boolean
          codigo: string
          created_at: string
          descricao: string | null
          escopo: string
          nivel: number
          nome: string
          updated_at: string
        }
        Insert: {
          ativo?: boolean
          codigo: string
          created_at?: string
          descricao?: string | null
          escopo: string
          nivel?: number
          nome: string
          updated_at?: string
        }
        Update: {
          ativo?: boolean
          codigo?: string
          created_at?: string
          descricao?: string | null
          escopo?: string
          nivel?: number
          nome?: string
          updated_at?: string
        }
        Relationships: []
      }
      linkai_permissoes: {
        Row: {
          codigo: string
          created_at: string
          descricao: string | null
          nome: string
        }
        Insert: {
          codigo: string
          created_at?: string
          descricao?: string | null
          nome: string
        }
        Update: {
          codigo?: string
          created_at?: string
          descricao?: string | null
          nome?: string
        }
        Relationships: []
      }
      linkai_user_convites: {
        Row: {
          criado_em: string
          criado_por: string | null
          email: string
          empresa_id: number
          id: string
          nome: string
          obra_id: string | null
          perfil_codigo: string
          status: string
          two_factor_policy: string
          updated_at: string
          vinculado_em: string | null
        }
        Insert: {
          criado_em?: string
          criado_por?: string | null
          email: string
          empresa_id: number
          id?: string
          nome: string
          obra_id?: string | null
          perfil_codigo: string
          status?: string
          two_factor_policy?: string
          updated_at?: string
          vinculado_em?: string | null
        }
        Update: {
          criado_em?: string
          criado_por?: string | null
          email?: string
          empresa_id?: number
          id?: string
          nome?: string
          obra_id?: string | null
          perfil_codigo?: string
          status?: string
          two_factor_policy?: string
          updated_at?: string
          vinculado_em?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "linkai_user_convites_empresa_id_fkey"
            columns: ["empresa_id"]
            isOneToOne: false
            referencedRelation: "empresas"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "linkai_user_convites_obra_id_fkey"
            columns: ["obra_id"]
            isOneToOne: false
            referencedRelation: "linkai_obras"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "linkai_user_convites_perfil_codigo_fkey"
            columns: ["perfil_codigo"]
            isOneToOne: false
            referencedRelation: "linkai_perfis_internos"
            referencedColumns: ["codigo"]
          },
        ]
      }
      linkai_usuario_obras: {
        Row: {
          ativo: boolean
          created_at: string
          id: string
          obra_id: string
          perfil_codigo: string
          principal: boolean
          updated_at: string
          usuario_id: number
        }
        Insert: {
          ativo?: boolean
          created_at?: string
          id?: string
          obra_id: string
          perfil_codigo: string
          principal?: boolean
          updated_at?: string
          usuario_id: number
        }
        Update: {
          ativo?: boolean
          created_at?: string
          id?: string
          obra_id?: string
          perfil_codigo?: string
          principal?: boolean
          updated_at?: string
          usuario_id?: number
        }
        Relationships: [
          {
            foreignKeyName: "linkai_usuario_obras_obra_id_fkey"
            columns: ["obra_id"]
            isOneToOne: false
            referencedRelation: "linkai_obras"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "linkai_usuario_obras_perfil_codigo_fkey"
            columns: ["perfil_codigo"]
            isOneToOne: false
            referencedRelation: "linkai_perfis_internos"
            referencedColumns: ["codigo"]
          },
          {
            foreignKeyName: "linkai_usuario_obras_usuario_id_fkey"
            columns: ["usuario_id"]
            isOneToOne: false
            referencedRelation: "usuarios"
            referencedColumns: ["id"]
          },
        ]
      }
      linkai_usuario_permissoes: {
        Row: {
          concedida: boolean
          created_at: string
          permissao_codigo: string
          updated_at: string
          usuario_id: number
        }
        Insert: {
          concedida?: boolean
          created_at?: string
          permissao_codigo: string
          updated_at?: string
          usuario_id: number
        }
        Update: {
          concedida?: boolean
          created_at?: string
          permissao_codigo?: string
          updated_at?: string
          usuario_id?: number
        }
        Relationships: [
          {
            foreignKeyName: "linkai_usuario_permissoes_permissao_codigo_fkey"
            columns: ["permissao_codigo"]
            isOneToOne: false
            referencedRelation: "linkai_permissoes"
            referencedColumns: ["codigo"]
          },
          {
            foreignKeyName: "linkai_usuario_permissoes_usuario_id_fkey"
            columns: ["usuario_id"]
            isOneToOne: false
            referencedRelation: "usuarios"
            referencedColumns: ["id"]
          },
        ]
      }
      lumina_jobs: {
        Row: {
          action: string
          attempts: number
          created_at: string
          empresa_id: number | null
          finished_at: string | null
          heartbeat_at: string | null
          id: string
          item_number: number
          leased_until: string | null
          message: string | null
          obra_id: string | null
          payload: Json
          queue_request_id: string | null
          requested_by: string
          started_at: string | null
          status: string
          updated_at: string
          worker_id: string | null
        }
        Insert: {
          action?: string
          attempts?: number
          created_at?: string
          empresa_id?: number | null
          finished_at?: string | null
          heartbeat_at?: string | null
          id?: string
          item_number?: number
          leased_until?: string | null
          message?: string | null
          obra_id?: string | null
          payload?: Json
          queue_request_id?: string | null
          requested_by: string
          started_at?: string | null
          status?: string
          updated_at?: string
          worker_id?: string | null
        }
        Update: {
          action?: string
          attempts?: number
          created_at?: string
          empresa_id?: number | null
          finished_at?: string | null
          heartbeat_at?: string | null
          id?: string
          item_number?: number
          leased_until?: string | null
          message?: string | null
          obra_id?: string | null
          payload?: Json
          queue_request_id?: string | null
          requested_by?: string
          started_at?: string | null
          status?: string
          updated_at?: string
          worker_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "lumina_jobs_empresa_id_fkey"
            columns: ["empresa_id"]
            isOneToOne: false
            referencedRelation: "empresas"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "lumina_jobs_obra_id_fkey"
            columns: ["obra_id"]
            isOneToOne: false
            referencedRelation: "linkai_obras"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "lumina_jobs_queue_request_id_fkey"
            columns: ["queue_request_id"]
            isOneToOne: false
            referencedRelation: "lumina_queue_requests"
            referencedColumns: ["id"]
          },
        ]
      }
      lumina_queue_logs: {
        Row: {
          action: string | null
          attempts: number
          empresa_id: number | null
          finished_at: string
          id: string
          item_number: number
          message: string | null
          obra_id: string | null
          payload: Json
          queue_item_id: string
          queue_number: number
          queue_request_id: string | null
          queued_at: string | null
          requested_by: string | null
          started_at: string | null
          status: string
          worker_id: string | null
        }
        Insert: {
          action?: string | null
          attempts?: number
          empresa_id?: number | null
          finished_at?: string
          id?: string
          item_number: number
          message?: string | null
          obra_id?: string | null
          payload?: Json
          queue_item_id: string
          queue_number: number
          queue_request_id?: string | null
          queued_at?: string | null
          requested_by?: string | null
          started_at?: string | null
          status: string
          worker_id?: string | null
        }
        Update: {
          action?: string | null
          attempts?: number
          empresa_id?: number | null
          finished_at?: string
          id?: string
          item_number?: number
          message?: string | null
          obra_id?: string | null
          payload?: Json
          queue_item_id?: string
          queue_number?: number
          queue_request_id?: string | null
          queued_at?: string | null
          requested_by?: string | null
          started_at?: string | null
          status?: string
          worker_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "lumina_queue_logs_obra_id_fkey"
            columns: ["obra_id"]
            isOneToOne: false
            referencedRelation: "linkai_obras"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "lumina_queue_logs_queue_request_id_fkey"
            columns: ["queue_request_id"]
            isOneToOne: false
            referencedRelation: "lumina_queue_requests"
            referencedColumns: ["id"]
          },
        ]
      }
      lumina_queue_requests: {
        Row: {
          action: string
          canceled_items: number
          completed_items: number
          created_at: string
          empresa_id: number | null
          failed_items: number
          finished_at: string | null
          id: string
          message: string | null
          obra_id: string | null
          queue_number: number
          requested_by: string
          started_at: string | null
          status: string
          total_items: number
          updated_at: string
        }
        Insert: {
          action?: string
          canceled_items?: number
          completed_items?: number
          created_at?: string
          empresa_id?: number | null
          failed_items?: number
          finished_at?: string | null
          id?: string
          message?: string | null
          obra_id?: string | null
          queue_number?: number
          requested_by: string
          started_at?: string | null
          status?: string
          total_items?: number
          updated_at?: string
        }
        Update: {
          action?: string
          canceled_items?: number
          completed_items?: number
          created_at?: string
          empresa_id?: number | null
          failed_items?: number
          finished_at?: string | null
          id?: string
          message?: string | null
          obra_id?: string | null
          queue_number?: number
          requested_by?: string
          started_at?: string | null
          status?: string
          total_items?: number
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "lumina_queue_requests_empresa_id_fkey"
            columns: ["empresa_id"]
            isOneToOne: false
            referencedRelation: "empresas"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "lumina_queue_requests_obra_id_fkey"
            columns: ["obra_id"]
            isOneToOne: false
            referencedRelation: "linkai_obras"
            referencedColumns: ["id"]
          },
        ]
      }
      notas_processadas: {
        Row: {
          arquivo_pdf: string
          chave_acesso: string | null
          cnpj_emitente: string | null
          created_at: string | null
          data_emissao: string | null
          empresa_id: number | null
          erro_processamento: string | null
          id: string
          medicao_vinculada: string | null
          numero_nf: string | null
          obra_id: string | null
          payload_lumina: Json | null
          pedido_vinculado: string | null
          serie: string | null
          status_lancamento: string | null
          status_matching: string | null
          updated_at: string | null
          valor_total: number | null
        }
        Insert: {
          arquivo_pdf: string
          chave_acesso?: string | null
          cnpj_emitente?: string | null
          created_at?: string | null
          data_emissao?: string | null
          empresa_id?: number | null
          erro_processamento?: string | null
          id?: string
          medicao_vinculada?: string | null
          numero_nf?: string | null
          obra_id?: string | null
          payload_lumina?: Json | null
          pedido_vinculado?: string | null
          serie?: string | null
          status_lancamento?: string | null
          status_matching?: string | null
          updated_at?: string | null
          valor_total?: number | null
        }
        Update: {
          arquivo_pdf?: string
          chave_acesso?: string | null
          cnpj_emitente?: string | null
          created_at?: string | null
          data_emissao?: string | null
          empresa_id?: number | null
          erro_processamento?: string | null
          id?: string
          medicao_vinculada?: string | null
          numero_nf?: string | null
          obra_id?: string | null
          payload_lumina?: Json | null
          pedido_vinculado?: string | null
          serie?: string | null
          status_lancamento?: string | null
          status_matching?: string | null
          updated_at?: string | null
          valor_total?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "notas_processadas_empresa_id_fkey"
            columns: ["empresa_id"]
            isOneToOne: false
            referencedRelation: "empresas"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "notas_processadas_obra_id_fkey"
            columns: ["obra_id"]
            isOneToOne: false
            referencedRelation: "linkai_obras"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "notas_processadas_pedido_vinculado_fkey"
            columns: ["pedido_vinculado"]
            isOneToOne: false
            referencedRelation: "pedidos_pendentes"
            referencedColumns: ["id"]
          },
        ]
      }
      noticias_construcao: {
        Row: {
          data_coleta: string
          data_publicacao: string | null
          fonte: string
          id: string
          relevante: boolean
          resumo: string | null
          titulo: string
          url: string
        }
        Insert: {
          data_coleta?: string
          data_publicacao?: string | null
          fonte: string
          id?: string
          relevante?: boolean
          resumo?: string | null
          titulo: string
          url: string
        }
        Update: {
          data_coleta?: string
          data_publicacao?: string | null
          fonte?: string
          id?: string
          relevante?: boolean
          resumo?: string | null
          titulo?: string
          url?: string
        }
        Relationships: []
      }
      pedidos_pendentes: {
        Row: {
          categoria: string | null
          cliente_obra: string | null
          cnpj_fornecedor: string
          condicao_pagamento: string | null
          conta_debito: string | null
          created_at: string | null
          empresa_id: number | null
          id: string
          numero_medicao: string | null
          numero_pedido: string | null
          obra_id: string | null
          qtd_parcelas_padrao: number | null
          status: string | null
          subcategoria: string | null
          tipo_fatura: string | null
          updated_at: string | null
          valor_medicao_liquido: number
        }
        Insert: {
          categoria?: string | null
          cliente_obra?: string | null
          cnpj_fornecedor: string
          condicao_pagamento?: string | null
          conta_debito?: string | null
          created_at?: string | null
          empresa_id?: number | null
          id?: string
          numero_medicao?: string | null
          numero_pedido?: string | null
          obra_id?: string | null
          qtd_parcelas_padrao?: number | null
          status?: string | null
          subcategoria?: string | null
          tipo_fatura?: string | null
          updated_at?: string | null
          valor_medicao_liquido: number
        }
        Update: {
          categoria?: string | null
          cliente_obra?: string | null
          cnpj_fornecedor?: string
          condicao_pagamento?: string | null
          conta_debito?: string | null
          created_at?: string | null
          empresa_id?: number | null
          id?: string
          numero_medicao?: string | null
          numero_pedido?: string | null
          obra_id?: string | null
          qtd_parcelas_padrao?: number | null
          status?: string | null
          subcategoria?: string | null
          tipo_fatura?: string | null
          updated_at?: string | null
          valor_medicao_liquido?: number
        }
        Relationships: [
          {
            foreignKeyName: "pedidos_pendentes_empresa_id_fkey"
            columns: ["empresa_id"]
            isOneToOne: false
            referencedRelation: "empresas"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "pedidos_pendentes_obra_id_fkey"
            columns: ["obra_id"]
            isOneToOne: false
            referencedRelation: "linkai_obras"
            referencedColumns: ["id"]
          },
        ]
      }
      regras_imposto: {
        Row: {
          aliquota_padrao: number | null
          ativo: boolean | null
          codigo_receita: string | null
          created_at: string | null
          fornecedor_ou_tipo_servico: string
          id: string
          imposto: string
          updated_at: string | null
        }
        Insert: {
          aliquota_padrao?: number | null
          ativo?: boolean | null
          codigo_receita?: string | null
          created_at?: string | null
          fornecedor_ou_tipo_servico: string
          id?: string
          imposto: string
          updated_at?: string | null
        }
        Update: {
          aliquota_padrao?: number | null
          ativo?: boolean | null
          codigo_receita?: string | null
          created_at?: string | null
          fornecedor_ou_tipo_servico?: string
          id?: string
          imposto?: string
          updated_at?: string | null
        }
        Relationships: []
      }
      robot_logs: {
        Row: {
          created_at: string | null
          empresa_id: number | null
          etapa: string | null
          id: string
          mensagem: string | null
          nota_id: string | null
          obra_id: string | null
          sucesso: boolean | null
        }
        Insert: {
          created_at?: string | null
          empresa_id?: number | null
          etapa?: string | null
          id?: string
          mensagem?: string | null
          nota_id?: string | null
          obra_id?: string | null
          sucesso?: boolean | null
        }
        Update: {
          created_at?: string | null
          empresa_id?: number | null
          etapa?: string | null
          id?: string
          mensagem?: string | null
          nota_id?: string | null
          obra_id?: string | null
          sucesso?: boolean | null
        }
        Relationships: [
          {
            foreignKeyName: "robot_logs_empresa_id_fkey"
            columns: ["empresa_id"]
            isOneToOne: false
            referencedRelation: "empresas"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "robot_logs_nota_id_fkey"
            columns: ["nota_id"]
            isOneToOne: false
            referencedRelation: "notas_processadas"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "robot_logs_obra_id_fkey"
            columns: ["obra_id"]
            isOneToOne: false
            referencedRelation: "linkai_obras"
            referencedColumns: ["id"]
          },
        ]
      }
      usuarios: {
        Row: {
          ariia_user_id: string | null
          ativo: boolean | null
          atualizado_em: string | null
          auth_user_id: string
          avatar_customized: boolean
          avatar_url: string | null
          criado_em: string | null
          email: string
          empresa_id: number | null
          id: number
          is_platform_superadmin: boolean
          lumina_credentials_updated_at: string | null
          lumina_password_ciphertext: string | null
          lumina_password_set: boolean
          lumina_username: string | null
          nome: string
          permissao: string | null
          two_factor_policy: string
        }
        Insert: {
          ariia_user_id?: string | null
          ativo?: boolean | null
          atualizado_em?: string | null
          auth_user_id: string
          avatar_customized?: boolean
          avatar_url?: string | null
          criado_em?: string | null
          email: string
          empresa_id?: number | null
          id?: number
          is_platform_superadmin?: boolean
          lumina_credentials_updated_at?: string | null
          lumina_password_ciphertext?: string | null
          lumina_password_set?: boolean
          lumina_username?: string | null
          nome: string
          permissao?: string | null
          two_factor_policy?: string
        }
        Update: {
          ariia_user_id?: string | null
          ativo?: boolean | null
          atualizado_em?: string | null
          auth_user_id?: string
          avatar_customized?: boolean
          avatar_url?: string | null
          criado_em?: string | null
          email?: string
          empresa_id?: number | null
          id?: number
          is_platform_superadmin?: boolean
          lumina_credentials_updated_at?: string | null
          lumina_password_ciphertext?: string | null
          lumina_password_set?: boolean
          lumina_username?: string | null
          nome?: string
          permissao?: string | null
          two_factor_policy?: string
        }
        Relationships: [
          {
            foreignKeyName: "usuarios_empresa_id_fkey"
            columns: ["empresa_id"]
            isOneToOne: false
            referencedRelation: "empresas"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      buscar_pedido_nf: {
        Args: { p_cnpj: string; p_valor: number }
        Returns: {
          numero_medicao: string
          numero_pedido: string
          pedido_id: string
        }[]
      }
      claim_lumina_job: {
        Args: { p_lease_seconds?: number; p_worker_id: string }
        Returns: {
          action: string
          attempts: number
          created_at: string
          empresa_id: number | null
          finished_at: string | null
          heartbeat_at: string | null
          id: string
          item_number: number
          leased_until: string | null
          message: string | null
          obra_id: string | null
          payload: Json
          queue_request_id: string | null
          requested_by: string
          started_at: string | null
          status: string
          updated_at: string
          worker_id: string | null
        }[]
        SetofOptions: {
          from: "*"
          to: "lumina_jobs"
          isOneToOne: false
          isSetofReturn: true
        }
      }
      custom_access_token_hook: { Args: { event: Json }; Returns: Json }
      enqueue_lumina_request: {
        Args: { p_action?: string; p_items?: Json; p_payload?: Json }
        Returns: {
          action: string
          canceled_items: number
          completed_items: number
          created_at: string
          empresa_id: number | null
          failed_items: number
          finished_at: string | null
          id: string
          message: string | null
          obra_id: string | null
          queue_number: number
          requested_by: string
          started_at: string | null
          status: string
          total_items: number
          updated_at: string
        }
        SetofOptions: {
          from: "*"
          to: "lumina_queue_requests"
          isOneToOne: true
          isSetofReturn: false
        }
      }
      finish_lumina_job: {
        Args: {
          p_job_id: string
          p_message: string
          p_status: string
          p_worker_id: string
        }
        Returns: boolean
      }
      get_usuario_atual: {
        Args: never
        Returns: {
          email: string
          empresa_id: number
          id: number
          nome: string
          permissao: string
        }[]
      }
      jwt_ariia_user_id: { Args: never; Returns: string }
      jwt_ativo: { Args: never; Returns: boolean }
      jwt_empresa_id: { Args: never; Returns: number }
      jwt_has_permissao: { Args: { _permissoes: string[] }; Returns: boolean }
      jwt_permissao: { Args: never; Returns: string }
      linkai_assign_user_to_obra: {
        Args: {
          p_obra_id: string
          p_perfil_codigo: string
          p_principal?: boolean
          p_usuario_id: number
        }
        Returns: {
          ativo: boolean
          created_at: string
          id: string
          obra_id: string
          perfil_codigo: string
          principal: boolean
          updated_at: string
          usuario_id: number
        }
        SetofOptions: {
          from: "*"
          to: "linkai_usuario_obras"
          isOneToOne: true
          isSetofReturn: false
        }
      }
      linkai_can_access_obra: { Args: { p_obra_id: string }; Returns: boolean }
      linkai_can_manage_empresa: {
        Args: { p_empresa_id: number }
        Returns: boolean
      }
      linkai_create_convite: {
        Args: {
          p_email: string
          p_nome: string
          p_obras?: Json
          p_perfil_codigo: string
          p_permissoes?: Json
          p_two_factor_policy: string
        }
        Returns: {
          criado_em: string
          criado_por: string | null
          email: string
          empresa_id: number
          id: string
          nome: string
          obra_id: string | null
          perfil_codigo: string
          status: string
          two_factor_policy: string
          updated_at: string
          vinculado_em: string | null
        }
        SetofOptions: {
          from: "*"
          to: "linkai_user_convites"
          isOneToOne: true
          isSetofReturn: false
        }
      }
      linkai_create_obra: {
        Args: {
          p_codigo: string
          p_empresa_id: number
          p_nome: string
          p_tipo?: string
        }
        Returns: {
          ativo: boolean
          codigo: string
          created_at: string
          empresa_id: number
          id: string
          nome: string
          tipo: string
          updated_at: string
        }
        SetofOptions: {
          from: "*"
          to: "linkai_obras"
          isOneToOne: true
          isSetofReturn: false
        }
      }
      linkai_current_empresa_id: { Args: never; Returns: number }
      linkai_current_usuario: {
        Args: never
        Returns: {
          ariia_user_id: string | null
          ativo: boolean | null
          atualizado_em: string | null
          auth_user_id: string
          avatar_customized: boolean
          avatar_url: string | null
          criado_em: string | null
          email: string
          empresa_id: number | null
          id: number
          is_platform_superadmin: boolean
          lumina_credentials_updated_at: string | null
          lumina_password_ciphertext: string | null
          lumina_password_set: boolean
          lumina_username: string | null
          nome: string
          permissao: string | null
          two_factor_policy: string
        }
        SetofOptions: {
          from: "*"
          to: "usuarios"
          isOneToOne: true
          isSetofReturn: false
        }
      }
      linkai_current_usuario_id: { Args: never; Returns: number }
      linkai_ensure_escritorio: {
        Args: { p_empresa_id: number }
        Returns: string
      }
      linkai_has_permissao: { Args: { _permissao: string }; Returns: boolean }
      linkai_is_platform_superadmin: { Args: never; Returns: boolean }
      linkai_is_supervisor: { Args: never; Returns: boolean }
      linkai_link_convite: {
        Args: { p_email: string }
        Returns: {
          criado_em: string
          criado_por: string | null
          email: string
          empresa_id: number
          id: string
          nome: string
          obra_id: string | null
          perfil_codigo: string
          status: string
          two_factor_policy: string
          updated_at: string
          vinculado_em: string | null
        }
        SetofOptions: {
          from: "*"
          to: "linkai_user_convites"
          isOneToOne: true
          isSetofReturn: false
        }
      }
      linkai_log_activity: {
        Args: {
          p_action: string
          p_finished_at?: string
          p_message?: string
          p_obra_id?: string
          p_payload?: Json
          p_started_at?: string
          p_status?: string
        }
        Returns: string
      }
      linkai_obra_principal: {
        Args: { p_usuario_id?: number }
        Returns: string
      }
      linkai_obras_visiveis: { Args: never; Returns: string[] }
      linkai_perfil_principal: {
        Args: { p_usuario_id?: number }
        Returns: string
      }
      linkai_set_usuario_acessos: {
        Args: {
          p_ativo?: boolean
          p_obras?: Json
          p_permissoes?: Json
          p_two_factor_policy?: string
          p_usuario_id: number
        }
        Returns: undefined
      }
      lumina_archive_job: {
        Args: { p_job_id: string; p_message: string; p_status: string }
        Returns: boolean
      }
      lumina_refresh_request: {
        Args: { p_request_id: string }
        Returns: undefined
      }
      release_lumina_job: {
        Args: { p_job_id: string; p_message: string; p_worker_id: string }
        Returns: boolean
      }
      renew_lumina_job: {
        Args: {
          p_job_id: string
          p_lease_seconds?: number
          p_worker_id: string
        }
        Returns: boolean
      }
      vincular_nf_pedido: {
        Args: { p_nf_id: string; p_pedido_id: string }
        Returns: undefined
      }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends (DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never) = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends (PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never) = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const
