import React, { useState, useEffect } from 'react'
import {
  Settings,
  Server,
  RefreshCw,
  Power,
  RotateCw,
  DownloadCloud,
  CheckCircle,
  AlertCircle,
  Shield,
  HardDrive,
  Cpu,
  Clock,
  Key,
  Globe,
  Sparkles,
  ExternalLink,
  Disc,
  FileText,
  X
} from 'lucide-react'
import {
  useSystemInfo,
  formatUptime,
  formatBytes
} from '@/hooks/useSystemStats'
import api, { SystemReleaseInfo, UpdateProgressStatus } from '@/services/api'

export default function SystemPage() {
  const { data: sysInfo, refetch: refetchInfo } = useSystemInfo()

  // Hostname state
  const [hostname, setHostname] = useState(sysInfo?.hostname || 'naybinho-nas')
  const [savingHostname, setSavingHostname] = useState(false)

  // Update & GitHub Releases state
  const [checkingUpdates, setCheckingUpdates] = useState(false)
  const [releaseInfo, setReleaseInfo] = useState<SystemReleaseInfo | null>(null)
  const [isUpdateModalOpen, setIsUpdateModalOpen] = useState(false)
  const [updateStatus, setUpdateStatus] = useState<UpdateProgressStatus | null>(null)
  const [isUpdating, setIsUpdating] = useState(false)

  // Power action state
  const [confirmModal, setConfirmModal] = useState<'reboot' | 'shutdown' | null>(null)
  const [actionInProgress, setActionInProgress] = useState(false)

  // Change Password
  const [currentPw, setCurrentPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [savingPw, setSavingPw] = useState(false)

  useEffect(() => {
    // Initial check on mount
    handleCheckUpdates(false)
  }, [])

  // Poll update progress if an update is currently running
  useEffect(() => {
    let interval: NodeJS.Timeout
    if (isUpdating) {
      interval = setInterval(async () => {
        try {
          const status = await api.getUpdateStatus()
          setUpdateStatus(status)
          if (!status.in_progress && status.progress.stage === 'completed') {
            setIsUpdating(false)
            refetchInfo()
          } else if (!status.in_progress && status.progress.stage === 'error') {
            setIsUpdating(false)
          }
        } catch {
          // ignore transient poll errors
        }
      }, 1500)
    }
    return () => clearInterval(interval)
  }, [isUpdating])

  const handleUpdateHostname = async () => {
    setSavingHostname(true)
    try {
      await api.setHostname(hostname)
      refetchInfo()
      alert('Hostname atualizado com sucesso!')
    } catch (err: any) {
      alert('Erro ao alterar hostname: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSavingHostname(false)
    }
  }

  const handleCheckUpdates = async (showAlert = true) => {
    setCheckingUpdates(true)
    try {
      const res = await api.checkUpdates()
      setReleaseInfo(res)
      if (showAlert) {
        if (res.has_update) {
          alert(`Nova versão disponível no GitHub: v${res.latest_version}! Uma nova imagem ISO foi lançada.`)
        } else {
          alert('Seu NayBinho NAS está rodando a versão mais recente.')
        }
      }
    } catch (err: any) {
      if (showAlert) {
        alert('Não foi possível verificar atualizações no momento.')
      }
    } finally {
      setCheckingUpdates(false)
    }
  }

  const handleStartSelfUpdate = async () => {
    if (!confirm('Deseja iniciar a atualização automática do NayBinho NAS agora? O sistema criará um backup e atualizará os serviços.')) {
      return
    }

    setIsUpdating(true)
    setIsUpdateModalOpen(true)
    try {
      await api.applyUpdates()
    } catch (err: any) {
      alert('Erro ao iniciar atualização: ' + (err.response?.data?.detail || err.message))
      setIsUpdating(false)
    }
  }

  const handlePowerAction = async () => {
    if (!confirmModal) return
    setActionInProgress(true)
    try {
      if (confirmModal === 'reboot') {
        await api.reboot()
        alert('O sistema está reiniciando...')
      } else {
        await api.shutdown()
        alert('O sistema está desligando...')
      }
      setConfirmModal(null)
    } catch (err: any) {
      alert('Falha na ação de energia: ' + (err.response?.data?.detail || err.message))
    } finally {
      setActionInProgress(false)
    }
  }

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!currentPw || !newPw) return
    setSavingPw(true)
    try {
      await api.changePassword(currentPw, newPw)
      alert('Senha alterada com sucesso!')
      setCurrentPw('')
      setNewPw('')
    } catch (err: any) {
      alert('Erro ao trocar senha: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSavingPw(false)
    }
  }

  const currentVersion = releaseInfo?.current_version || sysInfo?.version || '1.0.0'
  const hasUpdate = releaseInfo?.has_update || false

  return (
    <div className="space-y-6">
      {/* Banner de Atualização Disponível se houver nova ISO no GitHub */}
      {hasUpdate && releaseInfo && (
        <div className="bg-gradient-to-r from-blue-950/90 via-indigo-950/90 to-purple-950/90 border border-blue-500/50 p-5 rounded-2xl shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-start gap-3.5">
            <div className="p-2.5 bg-blue-600/30 border border-blue-400/40 rounded-xl text-blue-300">
              <Sparkles className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs uppercase font-extrabold tracking-wider px-2 py-0.5 rounded bg-blue-600 text-white">
                  Nova Versão Disponível
                </span>
                <span className="text-sm font-mono font-bold text-white">v{releaseInfo.latest_version}</span>
              </div>
              <h3 className="text-base font-bold text-white mt-1">
                {releaseInfo.release_title || `Atualização do NayBinho NAS v${releaseInfo.latest_version}`}
              </h3>
              <p className="text-xs text-blue-200/80 mt-0.5">
                Uma nova versão foi publicada no GitHub com nova imagem ISO e melhorias para o sistema.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto">
            {releaseInfo.iso_asset && (
              <a
                href={releaseInfo.iso_asset.download_url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white rounded-lg border border-slate-700 transition"
              >
                <Disc className="w-4 h-4 text-cyan-400" />
                Baixar ISO ({releaseInfo.iso_asset.size_mb} MB)
              </a>
            )}
            <button
              onClick={handleStartSelfUpdate}
              className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-xs font-bold text-white rounded-lg shadow-lg transition"
            >
              <DownloadCloud className="w-4 h-4" />
              Atualizar Sistema Agora
            </button>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Settings className="w-6 h-6 text-naybinho-accent" />
            Configurações do Sistema
          </h1>
          <p className="text-sm text-naybinho-muted">
            Gerenciamento do servidor, auto-atualizações via GitHub, controle de energia e identidade
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => handleCheckUpdates(true)}
            disabled={checkingUpdates}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-naybinho-border text-xs font-semibold text-white rounded-lg transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${checkingUpdates ? 'animate-spin' : ''}`} />
            {checkingUpdates ? 'Consultando...' : 'Verificar Atualizações'}
          </button>
        </div>
      </div>

      {/* Quick Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-card p-4">
          <span className="text-xs text-naybinho-muted uppercase font-semibold">Sistema Operacional</span>
          <p className="text-base font-bold text-white mt-1">Ubuntu 26.04.1 LTS</p>
          <p className="text-xs text-slate-400 mt-1">Kernel Linux 6.8+ Otimizado</p>
        </div>

        <div className="glass-card p-4">
          <span className="text-xs text-naybinho-muted uppercase font-semibold">Arquitetura</span>
          <p className="text-base font-bold text-white mt-1">x86_64 (amd64)</p>
          <p className="text-xs text-slate-400 mt-1">SMP Preempt Suportado</p>
        </div>

        <div className="glass-card p-4">
          <span className="text-xs text-naybinho-muted uppercase font-semibold">Tempo Ativo (Uptime)</span>
          <p className="text-base font-bold text-white mt-1">{sysInfo?.uptime ? formatUptime(sysInfo.uptime) : 'Online'}</p>
          <p className="text-xs text-slate-400 mt-1">Sem interrupções</p>
        </div>

        <div className="glass-card p-4">
          <span className="text-xs text-naybinho-muted uppercase font-semibold">Versão do NayBinho NAS</span>
          <div className="flex items-center gap-2 mt-1">
            <p className="text-base font-bold text-naybinho-accent font-mono">v{currentVersion}</p>
            {hasUpdate && (
              <span className="text-[10px] bg-amber-500/20 text-amber-400 border border-amber-500/30 px-1.5 py-0.2 rounded font-bold">
                Update disponível
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1">Canal Oficial GitHub</p>
        </div>
      </div>

      {/* Main Settings Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* GitHub Releases & Atualização do Sistema */}
        <div className="glass-card p-5 flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <DownloadCloud className="w-4 h-4 text-naybinho-accent" />
                Atualizações & Releases do GitHub
              </h2>
              <span className="text-xs font-mono text-naybinho-muted">
                {releaseInfo?.last_checked ? `Checado: ${new Date(releaseInfo.last_checked).toLocaleTimeString()}` : ''}
              </span>
            </div>
            <p className="text-xs text-naybinho-muted mt-1">
              O NayBinho NAS monitora o repositório oficial no GitHub. Sempre que uma nova ISO ou release for publicada, você será notificado para atualizar com um clique.
            </p>

            <div className="mt-4 p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Versão instalada:</span>
                <span className="font-mono font-bold text-white">v{currentVersion}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Última versão no GitHub:</span>
                <span className={`font-mono font-bold ${hasUpdate ? 'text-amber-400' : 'text-emerald-400'}`}>
                  v{releaseInfo?.latest_version || currentVersion}
                </span>
              </div>

              {releaseInfo?.iso_asset && (
                <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-xs">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <Disc className="w-3.5 h-3.5 text-cyan-400" /> Nova Imagem ISO:
                  </span>
                  <span className="font-mono text-cyan-300">
                    {releaseInfo.iso_asset.name} ({releaseInfo.iso_asset.size_mb} MB)
                  </span>
                </div>
              )}

              {releaseInfo?.system_packages_count ? (
                <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-xs">
                  <span className="text-slate-400">Pacotes do Ubuntu pendentes:</span>
                  <span className="text-slate-200">{releaseInfo.system_packages_count} pacotes</span>
                </div>
              ) : null}
            </div>

            {releaseInfo?.release_notes && (
              <div className="mt-3 p-3 bg-slate-950/60 rounded-lg border border-slate-800/80 text-xs text-slate-300">
                <p className="font-semibold text-slate-200 mb-1 flex items-center gap-1">
                  <FileText className="w-3.5 h-3.5 text-naybinho-accent" /> Notas da Versão:
                </p>
                <p className="text-[11px] text-naybinho-muted line-clamp-3 whitespace-pre-line">
                  {releaseInfo.release_notes}
                </p>
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center justify-end gap-2.5 pt-2 border-t border-naybinho-border/40">
            {releaseInfo?.iso_asset && (
              <a
                href={releaseInfo.iso_asset.download_url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 rounded-lg transition"
              >
                <Disc className="w-3.5 h-3.5 text-cyan-400" />
                Baixar ISO (.iso)
              </a>
            )}
            <button
              onClick={handleStartSelfUpdate}
              disabled={isUpdating}
              className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold text-white transition shadow ${
                hasUpdate
                  ? 'bg-naybinho-primary hover:bg-blue-600 shadow-blue-900/30'
                  : 'bg-slate-800 hover:bg-slate-700'
              }`}
            >
              <DownloadCloud className="w-3.5 h-3.5" />
              {hasUpdate ? 'Atualizar Sistema Automaticamente' : 'Forçar Reinstalação de Pacotes'}
            </button>
          </div>
        </div>

        {/* Hostname & Identity */}
        <div className="glass-card p-5 flex flex-col justify-between">
          <div>
            <h2 className="text-base font-semibold text-white mb-2 flex items-center gap-2">
              <Server className="w-4 h-4 text-naybinho-accent" />
              Identidade do Servidor
            </h2>
            <p className="text-xs text-naybinho-muted mb-4">
              Configure o nome do servidor na rede local. Acessível via <code>{hostname}.local</code>.
            </p>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-naybinho-muted block mb-1">Hostname da Máquina</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={hostname}
                    onChange={(e) => setHostname(e.target.value)}
                    className="flex-1 p-2 bg-naybinho-bg border border-naybinho-border rounded-lg text-sm text-white focus:outline-none"
                  />
                  <button
                    disabled={savingHostname}
                    onClick={handleUpdateHostname}
                    className="px-4 py-2 bg-naybinho-primary hover:bg-blue-600 text-xs font-semibold text-white rounded-lg transition"
                  >
                    {savingHostname ? 'Salvando...' : 'Aplicar'}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800 text-xs text-slate-400 mt-4">
            <span className="font-semibold text-slate-300">Dica:</span> Ao alterar o hostname, os compartilhamentos SMB e NFS serão reiniciados para refletir o novo nome na rede.
          </div>
        </div>

        {/* Security / Change Password */}
        <div className="glass-card p-5">
          <h2 className="text-base font-semibold text-white mb-2 flex items-center gap-2">
            <Key className="w-4 h-4 text-naybinho-accent" />
            Alteração de Credenciais
          </h2>
          <p className="text-xs text-naybinho-muted mb-4">
            Modifique a senha de administrador da interface web e SSH.
          </p>

          <form onSubmit={handleChangePassword} className="space-y-3">
            <div>
              <label className="text-xs font-semibold text-naybinho-muted block mb-1">Senha Atual</label>
              <input
                type="password"
                value={currentPw}
                onChange={(e) => setCurrentPw(e.target.value)}
                placeholder="••••••••"
                className="w-full p-2 bg-naybinho-bg border border-naybinho-border rounded-lg text-sm text-white focus:outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-naybinho-muted block mb-1">Nova Senha</label>
              <input
                type="password"
                value={newPw}
                onChange={(e) => setNewPw(e.target.value)}
                placeholder="••••••••"
                className="w-full p-2 bg-naybinho-bg border border-naybinho-border rounded-lg text-sm text-white focus:outline-none"
              />
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={savingPw}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white rounded-lg border border-naybinho-border transition"
              >
                {savingPw ? 'Alterando...' : 'Salvar Nova Senha'}
              </button>
            </div>
          </form>
        </div>

        {/* Power Controls */}
        <div className="glass-card p-5 flex flex-col justify-between">
          <div>
            <h2 className="text-base font-semibold text-white mb-2 flex items-center gap-2">
              <Power className="w-4 h-4 text-red-400" />
              Controle de Energia
            </h2>
            <p className="text-xs text-naybinho-muted mb-4">
              Reinicie ou desligue o servidor com segurança. Arrays RAID e bancos de dados serão sincronizados antes do encerramento.
            </p>

            <div className="p-3 bg-red-950/20 border border-red-900/40 rounded-xl space-y-1 mb-4">
              <p className="text-xs font-semibold text-red-300">Atenção ao desligar remotamente</p>
              <p className="text-[11px] text-red-400/80">
                O desligamento exige acesso físico ao botão de ligar ou Wake-on-LAN para religar a máquina.
              </p>
            </div>
          </div>

          <div className="flex gap-3 justify-end pt-4 border-t border-naybinho-border/40">
            <button
              onClick={() => setConfirmModal('reboot')}
              className="flex items-center gap-1.5 px-4 py-2 bg-amber-950/50 hover:bg-amber-900/60 border border-amber-800 text-xs font-semibold text-amber-200 rounded-lg transition"
            >
              <RotateCw className="w-3.5 h-3.5" />
              Reiniciar Sistema
            </button>
            <button
              onClick={() => setConfirmModal('shutdown')}
              className="flex items-center gap-1.5 px-4 py-2 bg-red-950/50 hover:bg-red-900/60 border border-red-800 text-xs font-semibold text-red-200 rounded-lg transition"
            >
              <Power className="w-3.5 h-3.5" />
              Desligar Servidor
            </button>
          </div>
        </div>
      </div>

      {/* Modal: Progresso da Auto-Atualização */}
      {isUpdateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-naybinho-card border border-naybinho-border rounded-xl p-6 max-w-lg w-full shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-naybinho-border/60 pb-3">
              <div className="flex items-center gap-2.5">
                <DownloadCloud className="w-5 h-5 text-naybinho-accent" />
                <h3 className="text-base font-bold text-white">Atualizador do NayBinho NAS</h3>
              </div>
              {!isUpdating && (
                <button onClick={() => setIsUpdateModalOpen(false)} className="text-naybinho-muted hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              )}
            </div>

            <div className="space-y-4">
              <div className="flex justify-between text-xs text-naybinho-muted">
                <span>{updateStatus?.progress.message || 'Processando atualização...'}</span>
                <span className="font-mono font-bold text-white">{updateStatus?.progress.percent || 10}%</span>
              </div>

              <div className="w-full bg-slate-900 h-2.5 rounded-full overflow-hidden border border-slate-800">
                <div
                  className="bg-gradient-to-r from-blue-600 to-indigo-500 h-full rounded-full transition-all duration-300"
                  style={{ width: `${updateStatus?.progress.percent || 10}%` }}
                />
              </div>

              <div className="space-y-2 pt-2">
                <div className="flex items-center gap-2 text-xs">
                  <CheckCircle className={`w-3.5 h-3.5 ${(updateStatus?.progress.percent || 0) >= 15 ? 'text-emerald-400' : 'text-slate-600'}`} />
                  <span className={(updateStatus?.progress.percent || 0) >= 15 ? 'text-slate-200' : 'text-slate-500'}>
                    Backup preventivo de banco de dados e configs
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <CheckCircle className={`w-3.5 h-3.5 ${(updateStatus?.progress.percent || 0) >= 60 ? 'text-emerald-400' : 'text-slate-600'}`} />
                  <span className={(updateStatus?.progress.percent || 0) >= 60 ? 'text-slate-200' : 'text-slate-500'}>
                    Download dos novos arquivos da release do GitHub
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <CheckCircle className={`w-3.5 h-3.5 ${(updateStatus?.progress.percent || 0) >= 75 ? 'text-emerald-400' : 'text-slate-600'}`} />
                  <span className={(updateStatus?.progress.percent || 0) >= 75 ? 'text-slate-200' : 'text-slate-500'}>
                    Aplicação dos novos serviços e interface web
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <CheckCircle className={`w-3.5 h-3.5 ${(updateStatus?.progress.percent || 0) >= 95 ? 'text-emerald-400' : 'text-slate-600'}`} />
                  <span className={(updateStatus?.progress.percent || 0) >= 95 ? 'text-slate-200' : 'text-slate-500'}>
                    Reinicialização atômica dos serviços
                  </span>
                </div>
              </div>
            </div>

            {updateStatus?.progress.stage === 'completed' && (
              <div className="pt-3 border-t border-naybinho-border/40 flex justify-end">
                <button
                  onClick={() => {
                    setIsUpdateModalOpen(false)
                    window.location.reload()
                  }}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white rounded-lg transition"
                >
                  Concluir e Recarregar Painel
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Confirmation Modal (Power Action) */}
      {confirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-naybinho-card border border-naybinho-border rounded-xl p-6 max-w-sm w-full shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-amber-400" />
              Confirmar Ação de Energia
            </h3>
            <p className="text-xs text-naybinho-muted">
              Tem certeza que deseja <strong>{confirmModal === 'reboot' ? 'reiniciar' : 'desligar'}</strong> o NayBinho NAS agora?
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <button
                disabled={actionInProgress}
                onClick={() => setConfirmModal(null)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 text-xs font-semibold text-slate-300 hover:text-white"
              >
                Cancelar
              </button>
              <button
                disabled={actionInProgress}
                onClick={handlePowerAction}
                className="px-4 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-xs font-semibold text-white"
              >
                {actionInProgress ? 'Executando...' : 'Confirmar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
