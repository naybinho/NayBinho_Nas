// NayBinho NAS — Main layout shell (Sidebar + Header + Outlet)

import React from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'
import WizardModal from '@/components/WizardModal'
import { useSystemInfo } from '@/hooks/useSystemStats'

export default function MainLayout() {
  const { data: sysInfo } = useSystemInfo()

  return (
    <div className="flex h-screen overflow-hidden bg-naybinho-bg">
      {/* Assistente de Primeiro Acesso */}
      <WizardModal />

      {/* Sidebar */}
      <Sidebar version={sysInfo?.version ?? 'v1.0.0'} />

      {/* Main area */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
