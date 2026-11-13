import React, { useState } from 'react'
import {
  Layers,
  ShieldCheck,
  AlertOctagon,
  PlusCircle,
  Trash2,
  CheckCircle,
  HelpCircle,
  Info,
  Server,
  RefreshCw,
  HardDrive
} from 'lucide-react'
import {
  useRaidArrays,
  useDisks,
  formatBytes
} from '@/hooks/useSystemStats'
import api, { RaidArray } from '@/services/api'

export default function RAID() {
  const { data: raidArrays = [], isLoading, refetch } = useRaidArrays()
  const { data: disks = [] } = useDisks()

  // Wizard state
  const [wizardOpen, setWizardOpen] = useState(false)
  const [wizardStep, setWizardStep] = useState<1 | 2 | 3 | 4>(1)
  const [raidLevel, setRaidLevel] = useState<number>(5)
  const [selectedDisks, setSelectedDisks] = useState<string[]>([])
  const [arrayName, setArrayName] = useState<string>('md0')
  const [creating, setCreating] = useState(false)

  // RAID descriptions & minimum drives
  const raidProfiles: Record<number, { name: string; minDisks: number; fault: string; desc: string }> = {
    0: {
      name: 'RAID 0 (Striping)',
      minDisks: 2,
      fault: 'Tolerância zero a falhas. Perda de 1 disco resulta em perda de todos os dados.',
      desc: 'Alta performance e aproveitamento de 100% da capacidade total, sem paridade.'
    },
    1: {
      name: 'RAID 1 (Mirroring)',
      minDisks: 2,
      fault: 'Suporta perda de até N-1 discos (espelhamento exato).',
      desc: 'Segurança elevada com espelhamento idêntico entre unidades.'
    },
    5: {
      name: 'RAID 5 (Parity Striping)',
      minDisks: 3,
      fault: 'Suporta perda de 1 disco sem perda de dados.',
      desc: 'Equilíbrio excelente entre velocidade, segurança e aproveitamento de armazenamento.'
    },
    6: {
      name: 'RAID 6 (Dual Parity)',
      minDisks: 4,
      fault: 'Suporta perda simultânea de até 2 discos.',
      desc: 'Alta redundância com dupla paridade, ideal para grandes pools de armazenamento.'
    },
    10: {
      name: 'RAID 10 (1+0 Striping & Mirroring)',
      minDisks: 4,
      fault: 'Suporta perda de até 1 disco por sub-par espelhado.',
      desc: 'Combina velocidade extrema de RAID 0 com a resiliência do RAID 1.'
    }
  }

  const toggleDiskSelection = (dev: string) => {
    setSelectedDisks(prev =>
      prev.includes(dev) ? prev.filter(d => d !== dev) : [...prev, dev]
    )
  }

  const handleCreateArray = async () => {
    setCreating(true)
    try {
      await api.createRaid({
        name: arrayName,
        level: raidLevel,
        devices: selectedDisks
      })
      setWizardOpen(false)
      setWizardStep(1)
      setSelectedDisks([])
      refetch()
    } catch (err: any) {
      alert('Erro ao criar array RAID: ' + (err.response?.data?.detail || err.message))
    } finally {
      setCreating(false)
    }
  }

  const handleDeleteArray = async (name: string) => {
    if (!confirm(`ATENÇÃO: Deseja realmente destruir o array RAID "${name}"? Todos os dados serão perdidos!`)) return
    try {
      await api.deleteRaid(name)
      refetch()
    } catch (err: any) {
      alert('Erro ao remover array: ' + (err.response?.data?.detail || err.message))
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Layers className="w-6 h-6 text-naybinho-accent" />
            Gerenciamento de Redundância e RAID
          </h1>
          <p className="text-sm text-naybinho-muted">
            Configuração de subsistema mdadm, tolerância a falhas e reconstrução de pools
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-naybinho-card border border-naybinho-border text-xs text-naybinho-text hover:text-white hover:bg-slate-800 transition"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Atualizar
          </button>
          <button
            onClick={() => {
              setWizardStep(1)
              setSelectedDisks([])
              setWizardOpen(true)
            }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-naybinho-primary text-xs font-semibold text-white hover:bg-blue-600 transition shadow-lg shadow-blue-900/30"
          >
            <PlusCircle className="w-3.5 h-3.5" /> Criar Novo Array RAID
          </button>
        </div>
      </div>

      {/* Arrays Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {raidArrays.map((raid) => (
          <div key={raid.name} className="glass-card p-5 relative overflow-hidden flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-naybinho-primary/20 flex items-center justify-center text-naybinho-accent font-mono font-bold text-sm">
                    R{raid.level}
                  </div>
                  <div>
                    <h3 className="font-bold text-white text-base leading-tight">{raid.name}</h3>
                    <p className="text-[11px] text-naybinho-muted">{raid.devices.length} Unidades físicas</p>
                  </div>
                </div>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                  raid.state === 'active' ? 'badge-healthy' : 'badge-error'
                }`}>
                  {raid.state}
                </span>
              </div>

              <div className="mt-4 p-3 bg-naybinho-bg rounded-lg border border-naybinho-border/50 text-xs space-y-2">
                <div className="flex justify-between">
                  <span className="text-naybinho-muted">Capacidade Total:</span>
                  <span className="font-semibold text-white">{formatBytes(raid.size)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-naybinho-muted">Dispositivos Ativos:</span>
                  <span className="font-semibold text-emerald-400">{raid.active_devices} / {raid.devices.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-naybinho-muted">Dispositivos em Falha:</span>
                  <span className={`font-semibold ${raid.failed_devices > 0 ? 'text-red-400' : 'text-slate-400'}`}>
                    {raid.failed_devices}
                  </span>
                </div>
              </div>

              <div className="mt-3 flex items-center gap-1.5 text-xs text-slate-300">
                <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                <span className="text-[11px]">{raid.fault_tolerance}</span>
              </div>

              {raid.rebuild_progress !== undefined && (
                <div className="mt-3">
                  <div className="flex justify-between text-[11px] text-amber-400 mb-1">
                    <span>Reconstruindo array...</span>
                    <span>{raid.rebuild_progress}%</span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-amber-400 h-full rounded-full transition-all duration-300"
                      style={{ width: `${raid.rebuild_progress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="mt-5 pt-3 border-t border-naybinho-border/60 flex items-center justify-between">
              <span className="text-[11px] font-mono text-slate-400 truncate max-w-[150px]">
                {raid.devices.join(', ')}
              </span>
              <button
                onClick={() => handleDeleteArray(raid.name)}
                className="text-xs text-red-400 hover:text-red-300 flex items-center gap-1 transition"
              >
                <Trash2 className="w-3.5 h-3.5" /> Excluir
              </button>
            </div>
          </div>
        ))}

        {raidArrays.length === 0 && !isLoading && (
          <div className="col-span-full text-center py-12 glass-card border border-dashed border-naybinho-border">
            <Layers className="w-10 h-10 text-naybinho-muted mx-auto mb-3" />
            <h3 className="text-base font-semibold text-white">Nenhum array RAID configurado</h3>
            <p className="text-xs text-naybinho-muted max-w-sm mx-auto mt-1 mb-4">
              Crie um novo array redundante com seus discos para proteger dados contra falhas de hardware.
            </p>
            <button
              onClick={() => {
                setWizardStep(1)
                setSelectedDisks([])
                setWizardOpen(true)
              }}
              className="px-4 py-2 rounded-lg bg-naybinho-primary text-xs font-semibold text-white hover:bg-blue-600 transition"
            >
              Iniciar Assistente de RAID
            </button>
          </div>
        )}
      </div>

      {/* Wizard Modal */}
      {wizardOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-naybinho-card border border-naybinho-border rounded-xl p-6 max-w-2xl w-full shadow-2xl">
            {/* Step indicator */}
            <div className="flex items-center justify-between border-b border-naybinho-border pb-4 mb-6">
              <div>
                <h3 className="text-lg font-bold text-white">Assistente de Criação de RAID</h3>
                <p className="text-xs text-naybinho-muted">Passo {wizardStep} de 4</p>
              </div>
              <div className="flex items-center gap-2">
                {[1, 2, 3, 4].map(s => (
                  <span
                    key={s}
                    className={`w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center ${
                      wizardStep === s
                        ? 'bg-naybinho-accent text-white'
                        : wizardStep > s
                        ? 'bg-emerald-600 text-white'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>

            {/* STEP 1: Escolha do Nível */}
            {wizardStep === 1 && (
              <div className="space-y-4">
                <h4 className="text-sm font-semibold text-white">Escolha o Nível RAID:</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {[0, 1, 5, 6, 10].map(level => {
                    const prof = raidProfiles[level]
                    const isSelected = raidLevel === level
                    return (
                      <div
                        key={level}
                        onClick={() => setRaidLevel(level)}
                        className={`p-3.5 rounded-xl border cursor-pointer transition ${
                          isSelected
                            ? 'bg-blue-900/30 border-naybinho-accent ring-1 ring-naybinho-accent'
                            : 'bg-naybinho-bg border-naybinho-border hover:bg-white/5'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-white text-sm">{prof.name}</span>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                            Min {prof.minDisks} discos
                          </span>
                        </div>
                        <p className="text-xs text-naybinho-muted mt-2">{prof.desc}</p>
                        <p className="text-[11px] text-amber-400 mt-1">{prof.fault}</p>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* STEP 2: Seleção de Discos */}
            {wizardStep === 2 && (
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <h4 className="text-sm font-semibold text-white">
                    Selecione os Discos Físicos (Mínimo {raidProfiles[raidLevel].minDisks}):
                  </h4>
                  <span className="text-xs text-naybinho-accent font-medium">
                    {selectedDisks.length} selecionados
                  </span>
                </div>

                <div className="max-h-64 overflow-y-auto space-y-2">
                  {disks.length === 0 ? (
                    <p className="text-sm text-naybinho-muted py-4 text-center">Nenhum disco físico detectado.</p>
                  ) : (
                    disks.map((d) => {
                      const isChecked = selectedDisks.includes(d.device)
                      return (
                        <div
                          key={d.device}
                          onClick={() => toggleDiskSelection(d.device)}
                          className={`p-3 rounded-lg border cursor-pointer flex items-center justify-between transition ${
                            isChecked
                              ? 'bg-blue-900/30 border-naybinho-accent'
                              : 'bg-naybinho-bg border-naybinho-border hover:bg-white/5'
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onChange={() => {}}
                              className="rounded text-naybinho-accent"
                            />
                            <div>
                              <span className="font-mono text-sm text-white font-medium">{d.device}</span>
                              <span className="text-xs text-naybinho-muted ml-2">({d.model})</span>
                            </div>
                          </div>
                          <span className="text-xs font-semibold text-slate-300">{formatBytes(d.size)}</span>
                        </div>
                      )
                    })
                  )}
                </div>
              </div>
            )}

            {/* STEP 3: Nome do Array */}
            {wizardStep === 3 && (
              <div className="space-y-4">
                <h4 className="text-sm font-semibold text-white">Identificação do Conjunto RAID:</h4>
                <div>
                  <label className="text-xs text-naybinho-muted block mb-1">Nome do Dispositivo md:</label>
                  <input
                    type="text"
                    value={arrayName}
                    onChange={(e) => setArrayName(e.target.value)}
                    placeholder="md0 ou storage_pool"
                    className="w-full p-2.5 bg-naybinho-bg border border-naybinho-border rounded-lg text-sm text-white focus:outline-none"
                  />
                  <p className="text-[11px] text-naybinho-muted mt-1.5">
                    O Linux irá criar o dispositivo de bloco em <code>/dev/{arrayName}</code>.
                  </p>
                </div>
              </div>
            )}

            {/* STEP 4: Confirmação */}
            {wizardStep === 4 && (
              <div className="space-y-4">
                <h4 className="text-sm font-semibold text-white">Revisão e Confirmação:</h4>
                <div className="p-4 bg-naybinho-bg rounded-lg border border-naybinho-border space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-naybinho-muted">Nome do Array:</span>
                    <span className="font-mono text-white font-semibold">{arrayName}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-naybinho-muted">Nível RAID:</span>
                    <span className="text-white font-semibold">{raidProfiles[raidLevel].name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-naybinho-muted">Discos Vinculados:</span>
                    <span className="font-mono text-white">{selectedDisks.join(', ')}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-naybinho-muted">Tolerância a Falhas:</span>
                    <span className="text-emerald-400">{raidProfiles[raidLevel].fault}</span>
                  </div>
                </div>

                <div className="p-3 bg-red-950/40 border border-red-800 rounded-lg text-red-400 text-xs flex items-center gap-2">
                  <AlertOctagon className="w-5 h-5 flex-shrink-0" />
                  <span>
                    Aviso: Os dados anteriores nas unidades selecionadas serão sobrescritos na inicialização do array.
                  </span>
                </div>
              </div>
            )}

            {/* Modal Controls */}
            <div className="mt-8 flex justify-between items-center pt-4 border-t border-naybinho-border">
              <button
                disabled={creating}
                onClick={() => {
                  if (wizardStep === 1) setWizardOpen(false)
                  else setWizardStep((prev) => (prev - 1) as any)
                }}
                className="px-4 py-2 rounded text-xs text-naybinho-muted hover:text-white"
              >
                {wizardStep === 1 ? 'Cancelar' : 'Voltar'}
              </button>

              {wizardStep < 4 ? (
                <button
                  disabled={wizardStep === 2 && selectedDisks.length < raidProfiles[raidLevel].minDisks}
                  onClick={() => setWizardStep((prev) => (prev + 1) as any)}
                  className="px-4 py-2 rounded text-xs font-semibold bg-naybinho-primary hover:bg-blue-600 text-white disabled:opacity-50 transition"
                >
                  Próximo
                </button>
              ) : (
                <button
                  disabled={creating}
                  onClick={handleCreateArray}
                  className="px-5 py-2 rounded text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white transition flex items-center gap-2"
                >
                  {creating ? 'Criando Array...' : 'Confirmar e Construir RAID'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
