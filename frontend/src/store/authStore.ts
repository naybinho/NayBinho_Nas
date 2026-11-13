// NayBinho NAS — Auth Store (Zustand)
// Persists JWT token and user session across page refreshes

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { User } from '@/services/api'

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean

  // Actions
  setAuth: (token: string, user: User) => void
  logout: () => void
  updateUser: (user: Partial<User>) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      isAuthenticated: false,

      setAuth: (token, user) => {
        // Also persist token in localStorage for the Axios interceptor
        localStorage.setItem('naybinho_token', token)
        set({ token, user, isAuthenticated: true })
      },

      logout: () => {
        localStorage.removeItem('naybinho_token')
        set({ token: null, user: null, isAuthenticated: false })
      },

      updateUser: (partial) => {
        const current = get().user
        if (current) {
          set({ user: { ...current, ...partial } })
        }
      },
    }),
    {
      name: 'naybinho-auth',
      storage: createJSONStorage(() => localStorage),
      // Don't persist sensitive fields — only user metadata
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
)
