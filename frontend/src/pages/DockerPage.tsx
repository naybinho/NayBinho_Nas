import React, { useState } from 'react'
import {
  Container,
  Play,
  Square,
  RotateCw,
  Trash2,
  Terminal,
  DownloadCloud,
  CheckCircle,
  XCircle,
  RefreshCw,
  Layers,
  Cpu,
  Activity
} from 'lucide-react'
import {
  useContainers,
  useImages,
  formatBytes
} from '@/hooks/useSystemStats'
import api, { DockerContainer, DockerImage } from '@/services/api'

export default function DockerPage() {
  const { data: containers = [], isLoading: loadingContainers, refetch: refetchContainers } = useContainers()
  const { data: images = [], isLoading: loadingImages, refetch: refetchImages } = useImages()

  // Logs modal state
  const [logsModalOpen, setLogsModalOpen] = useState(false)
  const [activeContainerLogs, setActiveContainerLogs] = useState<string>('')
  const [selectedContainerName, setSelectedContainerName] = useState<string>('')
  const [loadingLogs, setLoadingLogs] = useState(false)

  // Pull Image state
  const [pullModalOpen, setPullModalOpen] = useState(false)
  const [imageToPull, setImageToPull] = useState('')
  const [pulling, setPulling] = useState(false)

  // Action status
  const [actionInProgress, setActionInProgress] = useState<string | null>(null)

  const handleContainerAction = async (id: string, action: 'start' | 'stop' | 'restart' | 'remove') => {
    setActionInProgress(`${id}-${action}`)
    try {
      await api.containerAction(id, action)
      refetchContainers()
    } catch (err: any) {
      alert(`Falha na ação ${action}: ` + (err.response?.data?.detail || err.message))
    } finally {
      setActionInProgress(null)
    }
  }

  const handleOpenLogs = async (container: DockerContainer) => {
    setSelectedContainerName(container.name)
    setLogsModalOpen(true)
    setLoadingLogs(true)
    try {
      const logs = await api.getContainerLogs(container.id, 150)
      setActiveContainerLogs(logs || 'Nenhum log registrado para este container.')
    } catch {
      setActiveContainerLogs('[SYS] Não foi possível obter os logs do container ou serviço em standby.')
    } finally {
      setLoadingLogs(false)
    }
  }

  const handlePullImage = async () => {
    if (!imageToPull) return
    setPulling(true)
    try {
      await api.pullImage(imageToPull)
      setPullModalOpen(false)
      setImageToPull('')
      refetchImages()
    } catch (err: any) {
      alert('Falha ao baixar imagem: ' + (err.response?.data?.detail || err.message))
    } finally {
      setPulling(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Container className="w-6 h-6 text-naybinho-accent" />
            Gerenciador Docker
          </h1>
          <p className="text-sm text-naybinho-muted">
            Monitore contêineres em execução, microserviços e imagens Docker nativas
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => { refetchContainers(); refetchImages() }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-naybinho-card border border-naybinho-border text-xs text-naybinho-text hover:text-white hover:bg-slate-800 transition"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Atualizar
          </button>
          <button
            onClick={() => setPullModalOpen(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-naybinho-primary text-xs font-semibold text-white hover:bg-blue-600 transition shadow-lg shadow-blue-900/30"
          >
            <DownloadCloud className="w-3.5 h-3.5" /> Baixar Nova Imagem
          </button>
        </div>
      </div>

      {/* Containers List */}
      <div className="glass-card p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Container className="w-4 h-4 text-naybinho-accent" />
            Contêineres ({containers.length})
          </h2>
          <span className="text-xs text-emerald-400 font-medium">
            {containers.filter(c => c.status === 'running').length} Em execução
          </span>
        </div>

        {loadingContainers ? (
          <p className="text-sm text-naybinho-muted py-8 text-center">Carregando contêineres Docker...</p>
        ) : containers.length === 0 ? (
          <div className="text-center py-10 border border-dashed border-naybinho-border rounded-xl">
            <p className="text-sm text-naybinho-muted">Nenhum contêiner configurado ou em execução.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-naybinho-border text-naybinho-muted text-xs uppercase">
                  <th className="pb-3 font-semibold">Nome</th>
                  <th className="pb-3 font-semibold">Imagem</th>
                  <th className="pb-3 font-semibold">Status</th>
                  <th className="pb-3 font-semibold">Portas</th>
                  <th className="pb-3 font-semibold">Uso CPU / RAM</th>
                  <th className="pb-3 font-semibold text-right">Controles</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-naybinho-border/40">
                {containers.map((c) => {
                  const isRunning = c.status === 'running'
                  return (
                    <tr key={c.id} className="hover:bg-white/5 transition">
                      <td className="py-3.5 font-semibold text-white flex items-center gap-2">
                        <span className={`w-2.5 h-2.5 rounded-full ${isRunning ? 'bg-emerald-500' : 'bg-slate-600'}`} />
                        {c.name}
                      </td>
                      <td className="py-3.5 text-xs text-slate-300 font-mono">{c.image}</td>
                      <td className="py-3.5">
                        <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${
                          isRunning ? 'badge-healthy' : 'badge-muted'
                        }`}>
                          {c.status}
                        </span>
                      </td>
                      <td className="py-3.5 text-xs text-slate-400 font-mono">
                        {c.ports?.length > 0 ? c.ports.join(', ') : '-'}
                      </td>
                      <td className="py-3.5 text-xs text-slate-300">
                        <div className="flex items-center gap-3">
                          <span className="flex items-center gap-1">
                            <Cpu className="w-3.5 h-3.5 text-blue-400" />
                            {c.cpu_percent ? `${c.cpu_percent.toFixed(1)}%` : '0%'}
                          </span>
                          <span className="flex items-center gap-1">
                            <Activity className="w-3.5 h-3.5 text-indigo-400" />
                            {c.mem_usage ? formatBytes(c.mem_usage) : '0 MB'}
                          </span>
                        </div>
                      </td>
                      <td className="py-3.5 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {isRunning ? (
                            <button
                              disabled={actionInProgress === `${c.id}-stop`}
                              onClick={() => handleContainerAction(c.id, 'stop')}
                              title="Parar Container"
                              className="p-1.5 rounded bg-amber-950/40 text-amber-400 hover:bg-amber-900/60 border border-amber-800 transition"
                            >
                              <Square className="w-3.5 h-3.5" />
                            </button>
                          ) : (
                            <button
                              disabled={actionInProgress === `${c.id}-start`}
                              onClick={() => handleContainerAction(c.id, 'start')}
                              title="Iniciar Container"
                              className="p-1.5 rounded bg-emerald-950/40 text-emerald-400 hover:bg-emerald-900/60 border border-emerald-800 transition"
                            >
                              <Play className="w-3.5 h-3.5" />
                            </button>
                          )}

                          <button
                            disabled={actionInProgress === `${c.id}-restart`}
                            onClick={() => handleContainerAction(c.id, 'restart')}
                            title="Reiniciar Container"
                            className="p-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 transition"
                          >
                            <RotateCw className="w-3.5 h-3.5" />
                          </button>

                          <button
                            onClick={() => handleOpenLogs(c)}
                            title="Visualizar Logs"
                            className="p-1.5 rounded bg-slate-800 text-naybinho-accent hover:bg-slate-700 transition"
                          >
                            <Terminal className="w-3.5 h-3.5" />
                          </button>

                          <button
                            disabled={actionInProgress === `${c.id}-remove`}
                            onClick={() => {
                              if (confirm(`Remover o container "${c.name}"?`)) {
                                handleContainerAction(c.id, 'remove')
                              }
                            }}
                            title="Remover Container"
                            className="p-1.5 rounded bg-red-950/40 text-red-400 hover:bg-red-900/60 border border-red-800 transition"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Images List */}
      <div className="glass-card p-5">
        <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <Layers className="w-4 h-4 text-naybinho-accent" />
          Imagens Docker Locais ({images.length})
        </h2>

        {loadingImages ? (
          <p className="text-sm text-naybinho-muted py-6 text-center">Carregando catálogo de imagens...</p>
        ) : images.length === 0 ? (
          <div className="text-center py-8 text-naybinho-muted text-sm border border-dashed border-naybinho-border rounded-xl">
            Nenhuma imagem Docker instalada.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {images.map((img) => (
              <div key={img.id} className="p-3.5 rounded-lg bg-naybinho-bg border border-naybinho-border/60 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-white font-mono truncate max-w-[200px]">
                    {img.tags?.[0] || img.id.substring(0, 12)}
                  </p>
                  <p className="text-xs text-naybinho-muted mt-1">{formatBytes(img.size)}</p>
                </div>
                <span className="text-[10px] text-slate-400 font-mono bg-slate-800 px-2 py-0.5 rounded">
                  {img.created ? new Date(img.created).toLocaleDateString() : 'Local'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Logs Terminal Modal */}
      {logsModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-slate-950 border border-naybinho-border rounded-xl p-5 max-w-3xl w-full shadow-2xl flex flex-col h-[500px]">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-bold text-white font-mono">Logs: {selectedContainerName}</h3>
              </div>
              <button
                onClick={() => setLogsModalOpen(false)}
                className="text-xs text-slate-400 hover:text-white"
              >
                Fechar
              </button>
            </div>

            <div className="flex-1 overflow-y-auto mt-4 p-3 bg-black rounded-lg font-mono text-xs text-emerald-400 space-y-1 select-text">
              {loadingLogs ? (
                <p className="text-slate-500">Buscando stream de logs...</p>
              ) : (
                <pre className="whitespace-pre-wrap">{activeContainerLogs}</pre>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Pull Image Modal */}
      {pullModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-naybinho-card border border-naybinho-border rounded-xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-2">Baixar Imagem Docker</h3>
            <p className="text-xs text-naybinho-muted mb-4">
              Informe a tag da imagem no Docker Hub ou registro privado (ex: <code>nginx:latest</code>, <code>redis:alpine</code>).
            </p>

            <input
              type="text"
              placeholder="ex: portainer/portainer-ce:latest"
              value={imageToPull}
              onChange={(e) => setImageToPull(e.target.value)}
              className="w-full p-2.5 bg-naybinho-bg border border-naybinho-border rounded-lg text-sm text-white focus:outline-none mb-6"
            />

            <div className="flex justify-end gap-3">
              <button
                disabled={pulling}
                onClick={() => setPullModalOpen(false)}
                className="px-4 py-2 rounded text-xs text-naybinho-muted hover:text-white"
              >
                Cancelar
              </button>
              <button
                disabled={pulling || !imageToPull}
                onClick={handlePullImage}
                className="px-4 py-2 rounded text-xs font-semibold bg-naybinho-primary hover:bg-blue-600 text-white disabled:opacity-50 transition flex items-center gap-1.5"
              >
                {pulling ? 'Baixando Imagem...' : 'Iniciar Download'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
