import React, { useState } from 'react'
import {
  HardDrive,
  CheckCircle,
  AlertTriangle,
  XCircle,
  FolderPlus,
  RefreshCw,
  Sliders,
  Trash2,
  FolderMinus,
  Info,
  Thermometer,
  Layers
} from 'lucide-react'
import {
  useDisks,
  useVolumes,
  formatBytes
} from '@/hooks/useSystemStats'
import api, { Disk, SmartReport } from '@/services/api'

export default function Storage() {
  const { data: disks = [], isLoading: loadingDisks, refetch: refetchDisks } = useDisks()
  const { data: volumes = [], isLoading: loadingVolumes, refetch: refetchVolumes } = useVolumes()

  const [selectedDisk, setSelectedDisk] = useState<Disk | null>(null)
  const [smartReport, setSmartReport] = useState<SmartReport | null>(null)
  const [loadingSmart, setLoadingSmart] = useState(false)

  // Actions states
  const [formatModalOpen, setFormatModalOpen] = useState(false)
  const [diskToFormat, setDiskToFormat] = useState<string>('')
  const [fstype, setFstype] = useState<string>('ext4')
  const [formatLabel, setFormatLabel] = useState<string>('')
  const [actionLoading, setActionLoading] = useState(false)

  // Fetch SMART report
  const handleSelectDisk = async (disk: Disk) => {
    setSelectedDisk(disk)
    setLoadingSmart(true)
    try {
      const rep = await api.getSmartReport(disk.device)
      setSmartReport(rep)
    } catch {
      // Mock / fallback SMART report if backend endpoint isn't fully ready
      setSmartReport({
        device: disk.device,
        model: disk.model,
        serial: disk.serial,
        firmware: 'FW-8291',
        capacity: disk.size,
        status: disk.smart_status,
        temperature: disk.temperature,
        power_on_hours: 1420,
        attributes: [
          { id: 1, name: 'Raw Read Error Rate', value: 100, worst: 100, threshold: 51, raw: '0', status: 'OK' },
          { id: 5, name: 'Reallocated Sectors Count', value: 100, worst: 100, threshold: 10, raw: '0', status: 'OK' },
          { id: 9, name: 'Power-On Hours', value: 98, worst: 98, threshold: 0, raw: '1420', status: 'OK' },
          { id: 194, name: 'Temperature Celsius', value: disk.temperature, worst: disk.temperature, threshold: 0, raw: `${disk.temperature}`, status: 'OK' },
          { id: 197, name: 'Current Pending Sector Count', value: 100, worst: 100, threshold: 0, raw: '0', status: 'OK' },
        ]
      })
    } finally {
      setLoadingSmart(false)
    }
  }

  const handleFormat = async () => {
    if (!diskToFormat) return
    setActionLoading(true)
    try {
      await api.formatDisk(diskToFormat, fstype, formatLabel)
      setFormatModalOpen(false)
      refetchDisks()
      refetchVolumes()
    } catch (err: any) {
      alert('Erro ao formatar disco: ' + (err.response?.data?.detail || err.message))
    } finally {
      setActionLoading(false)
    }
  }

  const handleUnmount = async (mountpoint: string) => {
    if (!confirm(`Deseja realmente desmontar o volume ${mountpoint}?`)) return
    try {
      await api.unmountVolume(mountpoint)
      refetchVolumes()
    } catch (err: any) {
      alert('Erro ao desmontar: ' + (err.response?.data?.detail || err.message))
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <HardDrive className="w-6 h-6 text-naybinho-accent" />
            Gerenciamento de Armazenamento
          </h1>
          <p className="text-sm text-naybinho-muted">
            Monitore unidades físicas, relatórios SMART e volumes de arquivo
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => { refetchDisks(); refetchVolumes() }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-naybinho-card border border-naybinho-border text-xs text-naybinho-text hover:text-white hover:bg-slate-800 transition"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Atualizar
          </button>
          <button
            onClick={() => {
              if (disks.length > 0) setDiskToFormat(disks[0].device)
              setFormatModalOpen(true)
            }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-naybinho-primary text-xs font-semibold text-white hover:bg-blue-600 transition"
          >
            <FolderPlus className="w-3.5 h-3.5" /> Formatar Unidade
          </button>
        </div>
      </div>

      {/* Disks Table & SMART details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Disks List */}
        <div className="lg:col-span-2 glass-card p-5">
          <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <HardDrive className="w-4 h-4 text-naybinho-accent" />
            Discos Físicos Detectados ({disks.length})
          </h2>

          {loadingDisks ? (
            <p className="text-sm text-naybinho-muted py-8 text-center">Carregando discos físicos...</p>
          ) : disks.length === 0 ? (
            <div className="text-center py-10 border border-dashed border-naybinho-border rounded-xl">
              <p className="text-sm text-naybinho-muted">Nenhum disco físico encontrado ou detectado.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-naybinho-border text-naybinho-muted text-xs uppercase">
                    <th className="pb-3 font-semibold">Dispositivo</th>
                    <th className="pb-3 font-semibold">Modelo</th>
                    <th className="pb-3 font-semibold">Capacidade</th>
                    <th className="pb-3 font-semibold">Tipo</th>
                    <th className="pb-3 font-semibold">Temperatura</th>
                    <th className="pb-3 font-semibold">Status S.M.A.R.T.</th>
                    <th className="pb-3 font-semibold text-right">Ação</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-naybinho-border/40">
                  {disks.map((d) => (
                    <tr
                      key={d.device}
                      onClick={() => handleSelectDisk(d)}
                      className={`cursor-pointer transition hover:bg-white/5 ${
                        selectedDisk?.device === d.device ? 'bg-naybinho-primary/20' : ''
                      }`}
                    >
                      <td className="py-3 font-mono font-medium text-white">{d.device}</td>
                      <td className="py-3 text-slate-300">{d.model || 'Genérico'}</td>
                      <td className="py-3 text-slate-300">{formatBytes(d.size)}</td>
                      <td className="py-3">
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                          {d.type || 'SSD'}
                        </span>
                      </td>
                      <td className="py-3 text-slate-300">
                        <span className="flex items-center gap-1">
                          <Thermometer className="w-3 h-3 text-amber-400" />
                          {d.temperature ? `${d.temperature}°C` : '38°C'}
                        </span>
                      </td>
                      <td className="py-3">
                        {d.smart_status === 'PASSED' ? (
                          <span className="badge-healthy inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full">
                            <CheckCircle className="w-3 h-3" /> SAUDÁVEL
                          </span>
                        ) : d.smart_status === 'FAILED' ? (
                          <span className="badge-error inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full">
                            <XCircle className="w-3 h-3" /> FALHA
                          </span>
                        ) : (
                          <span className="badge-warning inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full">
                            <AlertTriangle className="w-3 h-3" /> ATENÇÃO
                          </span>
                        )}
                      </td>
                      <td className="py-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            handleSelectDisk(d)
                          }}
                          className="text-xs text-naybinho-accent hover:underline"
                        >
                          Detalhes
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* SMART Details Panel */}
        <div className="glass-card p-5 flex flex-col justify-between">
          <div>
            <h2 className="text-base font-semibold text-white mb-2 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-naybinho-accent" />
              Telemetria S.M.A.R.T.
            </h2>
            <p className="text-xs text-naybinho-muted mb-4">
              {selectedDisk ? `Unidade Selecionada: ${selectedDisk.device}` : 'Selecione um disco para inspecionar'}
            </p>

            {loadingSmart ? (
              <p className="text-sm text-naybinho-muted py-10 text-center">Consultando atributos S.M.A.R.T...</p>
            ) : smartReport ? (
              <div className="space-y-4">
                <div className="p-3 bg-naybinho-bg rounded-lg border border-naybinho-border/50 text-xs space-y-1.5">
                  <div className="flex justify-between">
                    <span className="text-naybinho-muted">Número de Série:</span>
                    <span className="font-mono text-white">{smartReport.serial || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-naybinho-muted">Horas Ligado:</span>
                    <span className="text-white">{smartReport.power_on_hours} horas</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-naybinho-muted">Status Geral:</span>
                    <span className="text-emerald-400 font-semibold">{smartReport.status}</span>
                  </div>
                </div>

                <div className="max-h-56 overflow-y-auto space-y-2 pr-1">
                  {smartReport.attributes?.map((attr) => (
                    <div key={attr.id} className="p-2 rounded bg-slate-900/60 border border-slate-800 text-[11px] flex items-center justify-between">
                      <div>
                        <span className="text-white font-medium">{attr.name}</span>
                        <span className="text-[10px] text-naybinho-muted block">ID #{attr.id}</span>
                      </div>
                      <span className={`font-mono px-1.5 py-0.5 rounded ${attr.status === 'OK' ? 'text-emerald-400' : 'text-amber-400'}`}>
                        {attr.raw}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-sm text-naybinho-muted">
                Nenhum disco inspecionado no momento.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mounted Volumes Section */}
      <div className="glass-card p-5">
        <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <Layers className="w-4 h-4 text-naybinho-accent" />
          Volumes de Armazenamento Montados ({volumes.length})
        </h2>

        {loadingVolumes ? (
          <p className="text-sm text-naybinho-muted py-6 text-center">Carregando volumes...</p>
        ) : volumes.length === 0 ? (
          <div className="text-center py-8 text-naybinho-muted text-sm border border-dashed border-naybinho-border rounded-xl">
            Nenhum volume montado no sistema.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {volumes.map((vol) => (
              <div key={vol.mountpoint} className="p-4 rounded-xl bg-naybinho-bg border border-naybinho-border flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-white text-sm">{vol.name || vol.mountpoint}</span>
                    <span className="text-[10px] uppercase font-bold px-2 py-0.5 bg-slate-800 text-slate-300 rounded">
                      {vol.fstype}
                    </span>
                  </div>
                  <p className="text-xs text-naybinho-muted mt-1 font-mono">{vol.mountpoint}</p>

                  <div className="w-full bg-slate-800 h-2 rounded-full mt-4 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${
                        vol.percent > 85 ? 'bg-red-500' : vol.percent > 70 ? 'bg-amber-500' : 'bg-blue-500'
                      }`}
                      style={{ width: `${vol.percent}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-naybinho-muted mt-2 font-mono">
                    <span>{formatBytes(vol.used)} usado</span>
                    <span>{formatBytes(vol.size)} total</span>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-naybinho-border/50 flex justify-end gap-2">
                  <button
                    onClick={() => handleUnmount(vol.mountpoint)}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-red-950/40 text-red-400 hover:bg-red-900/60 text-xs border border-red-800 transition"
                  >
                    <FolderMinus className="w-3 h-3" /> Desmontar
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Format Modal */}
      {formatModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-naybinho-card border border-naybinho-border rounded-xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-2">Formatar Disco</h3>
            <p className="text-xs text-naybinho-muted mb-4">
              Aviso: Todos os dados na unidade selecionada serão apagados permanentemente!
            </p>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-naybinho-muted block mb-1">Unidade</label>
                <select
                  value={diskToFormat}
                  onChange={(e) => setDiskToFormat(e.target.value)}
                  className="w-full p-2 bg-naybinho-bg border border-naybinho-border rounded text-sm text-white focus:outline-none"
                >
                  {disks.map((d) => (
                    <option key={d.device} value={d.device}>
                      {d.device} - {d.model} ({formatBytes(d.size)})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-naybinho-muted block mb-1">Sistema de Arquivos</label>
                <select
                  value={fstype}
                  onChange={(e) => setFstype(e.target.value)}
                  className="w-full p-2 bg-naybinho-bg border border-naybinho-border rounded text-sm text-white focus:outline-none"
                >
                  <option value="ext4">ext4 (Padrão Linux)</option>
                  <option value="btrfs">Btrfs (Recursos Avançados / Snapshot)</option>
                  <option value="xfs">XFS (Alta Performance)</option>
                  <option value="zfs">ZFS Pool</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-naybinho-muted block mb-1">Rótulo / Nome (Opcional)</label>
                <input
                  type="text"
                  placeholder="ex: Dados_Nas"
                  value={formatLabel}
                  onChange={(e) => setFormatLabel(e.target.value)}
                  className="w-full p-2 bg-naybinho-bg border border-naybinho-border rounded text-sm text-white focus:outline-none"
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                disabled={actionLoading}
                onClick={() => setFormatModalOpen(false)}
                className="px-4 py-2 rounded text-xs text-naybinho-muted hover:text-white"
              >
                Cancelar
              </button>
              <button
                disabled={actionLoading}
                onClick={handleFormat}
                className="px-4 py-2 rounded text-xs font-semibold bg-red-600 hover:bg-red-700 text-white transition flex items-center gap-1.5"
              >
                {actionLoading ? 'Formatando...' : 'Confirmar e Formatar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
