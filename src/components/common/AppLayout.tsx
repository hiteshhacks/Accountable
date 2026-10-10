import React from 'react';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { useWorkspace } from '../../context/WorkspaceContext';

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const { theme } = useWorkspace();
  return (
    <div className="ws-root flex min-h-screen" data-theme={theme}>
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col pl-[230px]">
        <TopBar />
        <main className="flex-1 px-6 py-8 lg:px-9 lg:py-10">
          <div className="mx-auto max-w-[1240px]">{children}</div>
        </main>
      </div>
    </div>
  );
}
