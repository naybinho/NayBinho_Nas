// NayBinho NAS — Login Page

import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Server, Eye, EyeOff, Loader2, Shield } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import api from '@/services/api'

export default function Login() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw]     = useState(false)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username || !password) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.login(username, password)
      setAuth(res.access_token, res.user)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail ?? 'Credenciais inválidas')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-naybinho-bg flex items-center justify-center p-4 bg-hero-pattern">
      {/* Ambient glows */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-32 -left-32 w-96 h-96 bg-naybinho-primary/20 rounded-full blur-3xl" />
        <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-naybinho-accent/10 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Card */}
        <div className="glass-card p-8">
          {/* Logo */}
          <div className="flex flex-col items-center mb-8">
            <div className="w-16 h-16 bg-gradient-to-br from-naybinho-primary to-naybinho-accent rounded-2xl flex items-center justify-center shadow-2xl shadow-blue-900/50 mb-4">
              <Server className="w-9 h-9 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">NayBinho NAS</h1>
            <p className="text-naybinho-muted text-sm mt-1">Home Lab Operating System</p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Username */}
            <div>
              <label className="block text-sm font-medium text-naybinho-text mb-1.5">
                Usuário
              </label>
              <input
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                className="
                  w-full px-4 py-2.5 rounded-lg
                  bg-naybinho-bg border border-naybinho-border
                  text-naybinho-text placeholder-naybinho-muted
                  focus:outline-none focus:ring-2 focus:ring-naybinho-accent/50 focus:border-naybinho-accent
                  transition-colors text-sm
                "
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-naybinho-text mb-1.5">
                Senha
              </label>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="
                    w-full px-4 py-2.5 pr-10 rounded-lg
                    bg-naybinho-bg border border-naybinho-border
                    text-naybinho-text placeholder-naybinho-muted
                    focus:outline-none focus:ring-2 focus:ring-naybinho-accent/50 focus:border-naybinho-accent
                    transition-colors text-sm
                  "
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-naybinho-muted hover:text-naybinho-text transition-colors"
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="px-4 py-3 rounded-lg bg-red-900/30 border border-red-700/50 text-red-400 text-sm">
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading || !username || !password}
              className="
                w-full py-2.5 rounded-lg font-semibold text-sm
                bg-gradient-to-r from-naybinho-primary to-naybinho-accent
                text-white shadow-lg shadow-blue-900/40
                hover:opacity-90 active:scale-[0.98]
                disabled:opacity-50 disabled:cursor-not-allowed
                transition-all flex items-center justify-center gap-2
              "
            >
              {loading ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Autenticando...</>
              ) : (
                <><Shield className="w-4 h-4" /> Entrar</>
              )}
            </button>
          </form>

          {/* Footer */}
          <p className="text-center text-naybinho-muted/60 text-xs mt-6">
            NayBinho NAS © {new Date().getFullYear()} — Acesso seguro
          </p>
        </div>
      </div>
    </div>
  )
}
