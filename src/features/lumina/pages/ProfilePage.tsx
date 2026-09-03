import { useEffect, useRef, useState, type ChangeEvent, type ReactNode } from "react";
import {
  BriefcaseBusiness,
  Camera,
  CheckCircle2,
  KeyRound,
  Mail,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { toast } from "sonner";

import type { LuminaSessionUser } from "../LuminaApp";
import { SectionHeader } from "../components/SectionHeader";
import { supabase } from "@/integrations/supabase/client";
import { getMeuPerfil, updateMyAvatar, type MeuPerfil } from "../services/profile.functions";

interface ProfilePageProps {
  initialUser: Pick<LuminaSessionUser, "nome" | "email" | "avatarUrl">;
  onProfileUpdated: (update: { avatarUrl?: string | null }) => void;
}

export function ProfilePage({ initialUser, onProfileUpdated }: ProfilePageProps) {
  const [profile, setProfile] = useState<MeuPerfil | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let cancelled = false;

    getMeuPerfil({ data: {} })
      .then((data) => {
        if (!cancelled) setProfile(data);
      })
      .catch((error) => {
        if (!cancelled) {
          toast.error(
            error instanceof Error ? error.message : "Não foi possível carregar o perfil.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const currentProfile =
    profile ??
    ({
      authUserId: "",
      usuarioId: 0,
      nome: initialUser.nome,
      email: initialUser.email,
      avatarUrl: initialUser.avatarUrl,
      empresaNome: null,
      perfilCodigo: "",
      perfilNome: "Carregando...",
      obras: [],
      luminaUsername: null,
      luminaPasswordSet: false,
      luminaCredentialsUpdatedAt: null,
    } satisfies MeuPerfil);

  async function handlePhotoChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    if (!new Set(["image/jpeg", "image/png", "image/webp"]).has(file.type)) {
      toast.error("Escolha uma imagem para a foto de perfil.");
      return;
    }
    if (file.size > 3 * 1024 * 1024) {
      toast.error("A foto deve ter no máximo 3 MB.");
      return;
    }
    if (!currentProfile.authUserId) {
      toast.error("O perfil ainda está carregando.");
      return;
    }

    const extension =
      file.name
        .split(".")
        .pop()
        ?.toLowerCase()
        .replace(/[^a-z0-9]/g, "") || "jpg";
    const path = `${currentProfile.authUserId}/avatar-${Date.now()}.${extension}`;
    setUploading(true);

    try {
      const { error: uploadError } = await supabase.storage
        .from("linkai-avatars")
        .upload(path, file, { cacheControl: "3600", contentType: file.type, upsert: false });
      if (uploadError) throw uploadError;

      const updated = await updateMyAvatar({ data: { path } });
      setProfile((current) => (current ? { ...current, avatarUrl: updated.avatarUrl } : current));
      onProfileUpdated({ avatarUrl: updated.avatarUrl });
      toast.success("Foto de perfil atualizada.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível atualizar a foto.");
    } finally {
      setUploading(false);
    }
  }

  function requestLuminaChange() {
    toast.info(
      "Um técnico já foi acionado para efetuar a troca do login Lumina. Você será avisado quando estiver concluída.",
    );
  }

  const initials = currentProfile.nome
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Conta"
        title="Meu Perfil"
        description="Consulte seus dados e mantenha o acesso inicial do Lumina vinculado à sua conta."
      />

      {loading ? <div className="loading-panel">Carregando perfil...</div> : null}

      <div className="profile-grid">
        <section className="content-band profile-card profile-identity-card">
          <div className="profile-avatar-wrap">
            <div className="profile-avatar">
              {currentProfile.avatarUrl ? (
                <img alt={`Foto de ${currentProfile.nome}`} src={currentProfile.avatarUrl} />
              ) : (
                initials || "LA"
              )}
            </div>
            <button
              aria-label="Trocar foto de perfil"
              className="icon-button profile-avatar-action"
              disabled={uploading || loading}
              onClick={() => fileInput.current?.click()}
              title="Trocar foto de perfil"
              type="button"
            >
              <Camera size={16} />
            </button>
            <input
              ref={fileInput}
              accept="image/png,image/jpeg,image/webp"
              className="hidden-file-input"
              onChange={(event) => void handlePhotoChange(event)}
              type="file"
            />
          </div>
          <div className="profile-identity-copy">
            <span className="eyebrow">Usuário LinkAI</span>
            <h2>{currentProfile.nome}</h2>
            <p>{currentProfile.email}</p>
            {uploading ? <small>Enviando nova foto...</small> : null}
          </div>
        </section>

        <section className="content-band profile-card">
          <div className="profile-card-heading">
            <UserRound aria-hidden="true" size={18} />
            <div>
              <h3>Dados cadastrados</h3>
              <p>Nome, e-mail e vínculo definidos pela organização.</p>
            </div>
          </div>
          <div className="profile-data-list">
            <ProfileData icon={<UserRound size={15} />} label="Nome" value={currentProfile.nome} />
            <ProfileData icon={<Mail size={15} />} label="E-mail" value={currentProfile.email} />
            <ProfileData
              icon={<BriefcaseBusiness size={15} />}
              label="Empresa"
              value={currentProfile.empresaNome ?? "Não vinculada"}
            />
            <ProfileData
              icon={<ShieldCheck size={15} />}
              label="Função"
              value={currentProfile.perfilNome}
            />
          </div>
        </section>

        <section className="content-band profile-card profile-access-card">
          <div className="profile-card-heading">
            <KeyRound aria-hidden="true" size={18} />
            <div>
              <h3>Acesso ao Lumina</h3>
              <p>Usado pela máquina disponível para realizar seu lançamento.</p>
            </div>
          </div>
          <div className="profile-data-list">
            <ProfileData
              icon={<KeyRound size={15} />}
              label="Usuário Lumina"
              value={currentProfile.luminaUsername ?? "Ainda não configurado"}
            />
            <ProfileData
              icon={<ShieldCheck size={15} />}
              label="Senha Lumina"
              value={currentProfile.luminaPasswordSet ? "************" : "Ainda não configurada"}
            />
          </div>
          <div className="profile-access-actions">
            <span className="field-hint">
              {currentProfile.luminaCredentialsUpdatedAt
                ? `Cadastrado em ${new Date(currentProfile.luminaCredentialsUpdatedAt).toLocaleDateString("pt-BR")}.`
                : "O cadastro será solicitado ao iniciar o primeiro lançamento."}
            </span>
            <button className="button ghost" onClick={requestLuminaChange} type="button">
              <KeyRound aria-hidden="true" size={14} />
              Alterar login Lumina
            </button>
          </div>
        </section>

        <section className="content-band profile-card">
          <div className="profile-card-heading">
            <BriefcaseBusiness aria-hidden="true" size={18} />
            <div>
              <h3>Vínculos de acesso</h3>
              <p>Obra e função são administradas pela empresa e não podem ser alteradas aqui.</p>
            </div>
          </div>
          <div className="profile-work-list">
            {currentProfile.obras.length === 0 ? (
              <p className="hint">Nenhuma obra atribuída.</p>
            ) : (
              currentProfile.obras.map((obra) => (
                <div className="profile-work-row" key={obra.id}>
                  <div>
                    <strong>{obra.tipo === "escritorio" ? "ESCRITORIO" : obra.nome}</strong>
                    <span>{obra.codigo}</span>
                  </div>
                  <span className="status-badge status-info">
                    {obra.perfilNome}
                    {obra.principal ? " · Principal" : ""}
                  </span>
                </div>
              ))
            )}
          </div>
          <div className="profile-readonly-note">
            <CheckCircle2 aria-hidden="true" size={14} />
            Para mudar obra ou função, procure o supervisor da empresa.
          </div>
        </section>
      </div>
    </div>
  );
}

function ProfileData({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="profile-data-row">
      <span className="profile-data-icon">{icon}</span>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  );
}
