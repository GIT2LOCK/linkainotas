export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[];

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.15";
  };
  public: {
    Tables: {
      empresas: {
        Row: {
          cnpj: string | null;
          criado_em: string | null;
          id: number;
          nome_fantasia: string;
          razao_social: string | null;
        };
        Insert: {
          cnpj?: string | null;
          criado_em?: string | null;
          id: number;
          nome_fantasia: string;
          razao_social?: string | null;
        };
        Update: {
          cnpj?: string | null;
          criado_em?: string | null;
          id?: number;
          nome_fantasia?: string;
          razao_social?: string | null;
        };
        Relationships: [];
      };
      indicadores_construcao: {
        Row: {
          codigo: string;
          data_atualizacao: string;
          data_referencia: string;
          fonte: string | null;
          id: string;
          nome: string;
          unidade: string | null;
          valor: number;
        };
        Insert: {
          codigo: string;
          data_atualizacao?: string;
          data_referencia: string;
          fonte?: string | null;
          id?: string;
          nome: string;
          unidade?: string | null;
          valor: number;
        };
        Update: {
          codigo?: string;
          data_atualizacao?: string;
          data_referencia?: string;
          fonte?: string | null;
          id?: string;
          nome?: string;
          unidade?: string | null;
          valor?: number;
        };
        Relationships: [];
      };
      indicadores_historico: {
        Row: {
          codigo: string;
          created_at: string;
          data_referencia: string;
          id: string;
          valor: number;
        };
        Insert: {
          codigo: string;
          created_at?: string;
          data_referencia: string;
          id?: string;
          valor: number;
        };
        Update: {
          codigo?: string;
          created_at?: string;
          data_referencia?: string;
          id?: string;
          valor?: number;
        };
        Relationships: [];
      };
      notas_processadas: {
        Row: {
          arquivo_pdf: string;
          chave_acesso: string | null;
          cnpj_emitente: string | null;
          created_at: string | null;
          data_emissao: string | null;
          erro_processamento: string | null;
          id: string;
          medicao_vinculada: string | null;
          numero_nf: string | null;
          payload_lumina: Json | null;
          pedido_vinculado: string | null;
          serie: string | null;
          status_lancamento: string | null;
          status_matching: string | null;
          updated_at: string | null;
          valor_total: number | null;
        };
        Insert: {
          arquivo_pdf: string;
          chave_acesso?: string | null;
          cnpj_emitente?: string | null;
          created_at?: string | null;
          data_emissao?: string | null;
          erro_processamento?: string | null;
          id?: string;
          medicao_vinculada?: string | null;
          numero_nf?: string | null;
          payload_lumina?: Json | null;
          pedido_vinculado?: string | null;
          serie?: string | null;
          status_lancamento?: string | null;
          status_matching?: string | null;
          updated_at?: string | null;
          valor_total?: number | null;
        };
        Update: {
          arquivo_pdf?: string;
          chave_acesso?: string | null;
          cnpj_emitente?: string | null;
          created_at?: string | null;
          data_emissao?: string | null;
          erro_processamento?: string | null;
          id?: string;
          medicao_vinculada?: string | null;
          numero_nf?: string | null;
          payload_lumina?: Json | null;
          pedido_vinculado?: string | null;
          serie?: string | null;
          status_lancamento?: string | null;
          status_matching?: string | null;
          updated_at?: string | null;
          valor_total?: number | null;
        };
        Relationships: [
          {
            foreignKeyName: "notas_processadas_pedido_vinculado_fkey";
            columns: ["pedido_vinculado"];
            isOneToOne: false;
            referencedRelation: "pedidos_pendentes";
            referencedColumns: ["id"];
          },
        ];
      };
      noticias_construcao: {
        Row: {
          data_coleta: string;
          data_publicacao: string | null;
          fonte: string;
          id: string;
          relevante: boolean;
          resumo: string | null;
          titulo: string;
          url: string;
        };
        Insert: {
          data_coleta?: string;
          data_publicacao?: string | null;
          fonte: string;
          id?: string;
          relevante?: boolean;
          resumo?: string | null;
          titulo: string;
          url: string;
        };
        Update: {
          data_coleta?: string;
          data_publicacao?: string | null;
          fonte?: string;
          id?: string;
          relevante?: boolean;
          resumo?: string | null;
          titulo?: string;
          url?: string;
        };
        Relationships: [];
      };
      pedidos_pendentes: {
        Row: {
          categoria: string | null;
          cliente_obra: string | null;
          cnpj_fornecedor: string;
          condicao_pagamento: string | null;
          conta_debito: string | null;
          created_at: string | null;
          id: string;
          numero_medicao: string | null;
          numero_pedido: string | null;
          qtd_parcelas_padrao: number | null;
          status: string | null;
          subcategoria: string | null;
          tipo_fatura: string | null;
          updated_at: string | null;
          valor_medicao_liquido: number;
        };
        Insert: {
          categoria?: string | null;
          cliente_obra?: string | null;
          cnpj_fornecedor: string;
          condicao_pagamento?: string | null;
          conta_debito?: string | null;
          created_at?: string | null;
          id?: string;
          numero_medicao?: string | null;
          numero_pedido?: string | null;
          qtd_parcelas_padrao?: number | null;
          status?: string | null;
          subcategoria?: string | null;
          tipo_fatura?: string | null;
          updated_at?: string | null;
          valor_medicao_liquido: number;
        };
        Update: {
          categoria?: string | null;
          cliente_obra?: string | null;
          cnpj_fornecedor?: string;
          condicao_pagamento?: string | null;
          conta_debito?: string | null;
          created_at?: string | null;
          id?: string;
          numero_medicao?: string | null;
          numero_pedido?: string | null;
          qtd_parcelas_padrao?: number | null;
          status?: string | null;
          subcategoria?: string | null;
          tipo_fatura?: string | null;
          updated_at?: string | null;
          valor_medicao_liquido?: number;
        };
        Relationships: [];
      };
      regras_imposto: {
        Row: {
          aliquota_padrao: number | null;
          ativo: boolean | null;
          codigo_receita: string | null;
          created_at: string | null;
          fornecedor_ou_tipo_servico: string;
          id: string;
          imposto: string;
          updated_at: string | null;
        };
        Insert: {
          aliquota_padrao?: number | null;
          ativo?: boolean | null;
          codigo_receita?: string | null;
          created_at?: string | null;
          fornecedor_ou_tipo_servico: string;
          id?: string;
          imposto: string;
          updated_at?: string | null;
        };
        Update: {
          aliquota_padrao?: number | null;
          ativo?: boolean | null;
          codigo_receita?: string | null;
          created_at?: string | null;
          fornecedor_ou_tipo_servico?: string;
          id?: string;
          imposto?: string;
          updated_at?: string | null;
        };
        Relationships: [];
      };
      robot_logs: {
        Row: {
          created_at: string | null;
          etapa: string | null;
          id: string;
          mensagem: string | null;
          nota_id: string | null;
          sucesso: boolean | null;
        };
        Insert: {
          created_at?: string | null;
          etapa?: string | null;
          id?: string;
          mensagem?: string | null;
          nota_id?: string | null;
          sucesso?: boolean | null;
        };
        Update: {
          created_at?: string | null;
          etapa?: string | null;
          id?: string;
          mensagem?: string | null;
          nota_id?: string | null;
          sucesso?: boolean | null;
        };
        Relationships: [
          {
            foreignKeyName: "robot_logs_nota_id_fkey";
            columns: ["nota_id"];
            isOneToOne: false;
            referencedRelation: "notas_processadas";
            referencedColumns: ["id"];
          },
        ];
      };
      usuarios: {
        Row: {
          ariia_user_id: string | null;
          ativo: boolean | null;
          atualizado_em: string | null;
          auth_user_id: string;
          avatar_url: string | null;
          criado_em: string | null;
          email: string;
          empresa_id: number | null;
          id: number;
          nome: string;
          permissao: string | null;
        };
        Insert: {
          ariia_user_id?: string | null;
          ativo?: boolean | null;
          atualizado_em?: string | null;
          auth_user_id: string;
          avatar_url?: string | null;
          criado_em?: string | null;
          email: string;
          empresa_id?: number | null;
          id?: number;
          nome: string;
          permissao?: string | null;
        };
        Update: {
          ariia_user_id?: string | null;
          ativo?: boolean | null;
          atualizado_em?: string | null;
          auth_user_id?: string;
          avatar_url?: string | null;
          criado_em?: string | null;
          email?: string;
          empresa_id?: number | null;
          id?: number;
          nome?: string;
          permissao?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: "usuarios_empresa_id_fkey";
            columns: ["empresa_id"];
            isOneToOne: false;
            referencedRelation: "empresas";
            referencedColumns: ["id"];
          },
        ];
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      buscar_pedido_nf: {
        Args: { p_cnpj: string; p_valor: number };
        Returns: {
          numero_medicao: string;
          numero_pedido: string;
          pedido_id: string;
        }[];
      };
      custom_access_token_hook: { Args: { event: Json }; Returns: Json };
      get_usuario_atual: {
        Args: never;
        Returns: {
          email: string;
          empresa_id: number;
          id: number;
          nome: string;
          permissao: string;
        }[];
      };
      jwt_ariia_user_id: { Args: never; Returns: string };
      jwt_ativo: { Args: never; Returns: boolean };
      jwt_empresa_id: { Args: never; Returns: number };
      jwt_has_permissao: { Args: { _permissoes: string[] }; Returns: boolean };
      jwt_permissao: { Args: never; Returns: string };
      vincular_nf_pedido: {
        Args: { p_nf_id: string; p_pedido_id: string };
        Returns: undefined;
      };
    };
    Enums: {
      [_ in never]: never;
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
};

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">;

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">];

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R;
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] & DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R;
      }
      ? R
      : never
    : never;

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    keyof DefaultSchema["Tables"] | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I;
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I;
      }
      ? I
      : never
    : never;

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    keyof DefaultSchema["Tables"] | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U;
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U;
      }
      ? U
      : never
    : never;

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    keyof DefaultSchema["Enums"] | { schema: keyof DatabaseWithoutInternals },
  EnumName extends (DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never) = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never;

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    keyof DefaultSchema["CompositeTypes"] | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends (PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never) = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never;

export const Constants = {
  public: {
    Enums: {},
  },
} as const;
