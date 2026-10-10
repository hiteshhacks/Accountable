import React from 'react';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="flex min-h-screen bg-[#0A0805] text-[#F1E7CF]">
      <Sidebar />
      <div className="flex flex-1 flex-col pl-56">
        <TopBar />
        <main className="flex-1 p-8 lg:p-10">
          <div className="mx-auto max-w-[1200px]">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
