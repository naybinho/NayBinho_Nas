import React, { useState, useEffect } from 'react'
import { 
  Sparkles, 
  ShieldCheck, 
  HardDrive, 
  ShoppingBag, 
  ArrowRight, 
  CheckCircle2, 
  X,
  Server,
  Layers
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function WizardModal() {
  const [isOpen, setIsOpen] = useState(false)
  const [step, setStep] = useState(1)
  const navigate = useNavigate()

  useEffect(() => {
    const isCompleted = localStorage.getItem('naybinho_wizard_completed')
    if (!isCompleted) {
      setIsOpen(true)
    }
  }, [])

  const handleFinish = () => {
    localStorage.setItem('naybinho_wizard_completed', 'true')
    setIsOpen(false)
  }

  const handleGoToApps = () => {
    handleFinish()
    navigate('/appstore')
  }

  const handleGoToStorage = () => {
    handleFinish()
    navigate('/raid')
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-2xl bg-gradient-to-b from-slate-900 to-slate-950 border border-cyan-500/30 rounded-2xl shadow-2xl p-6 md:p-8 text-slate-100 animate-in fade-in zoom-in-95 duration-200">
        
        {/* Botão Fechar */}
        <button 
          onClick={handleFinish} 
          className="absolute top-5 right-5 text-slate-400 hover:text-slate-100 p-1.5 rounded-lg hover:bg-slate-800 transition"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Indicador de Passos */}
        <div className="flex items-center justify-between mb-8 pb-4 border-b border-slate-800/80">
          <div className="flex items-center gap-2">
            <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-cyan-500/20 text-cyan-400 font-bold border border-cyan-500/30">
              {step}
            </span>
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Passo {step} de 3
            </span>
          </div>

          <div className="flex gap-2">
            {[1, 2, 3].map((s) => (
              <div 
                key={s} 
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  s === step ? 'w-8 bg-cyan-400 shadow-[0_0_12px_rgba(6,182,212,0.8)]' : s < step ? 'w-4 bg-emerald-500' : 'w-4 bg-slate-800'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Conteúdo por Passo */}
        {step === 1 && (
          <div className="space-y-5 animate-in fade-in duration-150">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-cyan-500/10 border border-cyan-500/20 rounded-xl text-cyan-400">
                <Sparkles className="w-7 h-7" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">Bem-vindo ao NayBinho NAS!</h2>
                <p className="text-xs text-slate-400">O seu sistema de Home Lab inteligente, fácil e gratuito.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
              <div className="p-4 bg-slate-900/80 rounded-xl border border-slate-800/80 space-y-2">
                <Server className="w-5 h-5 text-cyan-400" />
                <h4 className="font-semibold text-xs text-slate-200">Home Lab Moderno</h4>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Gerencie todo o seu hardware, rede e temperatura em uma interface limpa e intuitiva.
                </p>
              </div>

              <div className="p-4 bg-slate-900/80 rounded-xl border border-slate-800/80 space-y-2">
                <Layers className="w-5 h-5 text-emerald-400" />
                <h4 className="font-semibold text-xs text-slate-200">Proteção RAID Total</h4>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  De 0 a 10 de tolerância. Agrupe seus HDDs com espelhamento para nunca perder arquivos.
                </p>
              </div>

              <div className="p-4 bg-slate-900/80 rounded-xl border border-slate-800/80 space-y-2">
                <ShoppingBag className="w-5 h-5 text-purple-400" />
                <h4 className="font-semibold text-xs text-slate-200">Apps em 1 Clique</h4>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Lojas nativas e da comunidade prontas para instalar Plex, Jellyfin, Nextcloud e mais.
                </p>
              </div>
            </div>

            <div className="flex justify-end pt-4">
              <button
                onClick={() => setStep(2)}
                className="flex items-center gap-2 px-5 py-2.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold rounded-xl text-xs transition shadow-lg shadow-cyan-500/20"
              >
                Próximo Passo <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-5 animate-in fade-in duration-150">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400">
                <ShieldCheck className="w-7 h-7" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">Segurança Inicial</h2>
                <p className="text-xs text-slate-400">Dicas rápidas para manter seu servidor seguro.</p>
              </div>
            </div>

            <div className="p-4 bg-slate-900/90 rounded-xl border border-slate-800 space-y-3 text-xs leading-relaxed">
              <div className="flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                <div>
                  <span className="font-semibold text-slate-200">Senha Padrão:</span> O usuário inicial é <code className="px-1.5 py-0.5 bg-slate-800 rounded text-cyan-300">admin</code> com senha <code className="px-1.5 py-0.5 bg-slate-800 rounded text-cyan-300">naybinho</code>. Você pode alterá-la na página de Sistema.
                </div>
              </div>

              <div className="flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                <div>
                  <span className="font-semibold text-slate-200">Compartilhamentos de Rede:</span> O Windows e Mac já podem encontrar o NAS pelo nome <code className="px-1.5 py-0.5 bg-slate-800 rounded text-cyan-300">\\naybinho-nas</code> na sua rede local.
                </div>
              </div>

              <div className="flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                <div>
                  <span className="font-semibold text-slate-200">Auto-Atualização:</span> O NayBinho NAS avisará automaticamente no cabeçalho quando houver novas versões de sistema ou melhorias.
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between pt-4">
              <button
                onClick={() => setStep(1)}
                className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-slate-200 transition"
              >
                Voltar
              </button>
              <button
                onClick={() => setStep(3)}
                className="flex items-center gap-2 px-5 py-2.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold rounded-xl text-xs transition shadow-lg shadow-cyan-500/20"
              >
                Próximo Passo <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-5 animate-in fade-in duration-150">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-purple-500/10 border border-purple-500/20 rounded-xl text-purple-400">
                <HardDrive className="w-7 h-7" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">Tudo Pronto para Começar!</h2>
                <p className="text-xs text-slate-400">Escolha o que você gostaria de fazer primeiro:</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 pt-1">
              <button
                onClick={handleGoToStorage}
                className="p-4 text-left bg-slate-900/90 hover:bg-slate-800/90 border border-slate-800 hover:border-cyan-500/50 rounded-xl transition group space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="p-2 bg-cyan-500/10 text-cyan-400 rounded-lg group-hover:scale-105 transition">
                    <HardDrive className="w-5 h-5" />
                  </span>
                  <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-cyan-400 group-hover:translate-x-1 transition" />
                </div>
                <h4 className="font-semibold text-sm text-slate-200">Configurar Discos & RAID</h4>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Criar pools de armazenamento protegido com RAID 0, 1, 5, 6, 10 ou ZFS.
                </p>
              </button>

              <button
                onClick={handleGoToApps}
                className="p-4 text-left bg-slate-900/90 hover:bg-slate-800/90 border border-slate-800 hover:border-purple-500/50 rounded-xl transition group space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="p-2 bg-purple-500/10 text-purple-400 rounded-lg group-hover:scale-105 transition">
                    <ShoppingBag className="w-5 h-5" />
                  </span>
                  <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-purple-400 group-hover:translate-x-1 transition" />
                </div>
                <h4 className="font-semibold text-sm text-slate-200">Instalar Aplicativos</h4>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Explorar a Loja de Apps e instalar Plex, Nextcloud, Home Assistant, etc.
                </p>
              </button>
            </div>

            <div className="flex items-center justify-between pt-4 border-t border-slate-800/80">
              <button
                onClick={() => setStep(2)}
                className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-slate-200 transition"
              >
                Voltar
              </button>
              <button
                onClick={handleFinish}
                className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold rounded-xl text-xs transition"
              >
                Explorar Painel Geral
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
