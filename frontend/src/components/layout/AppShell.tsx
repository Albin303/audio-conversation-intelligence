'use client';

import { MobileNav } from '@/components/layout/MobileNav';
import { Sidebar } from '@/components/layout/Sidebar';
import { useSidebar } from '@/providers/SidebarContext';
import { cn } from '@/lib/utils';

export function AppShell({ children }: { children: React.ReactNode }) {
  const { collapsed } = useSidebar();

  return (
    <>
      <MobileNav />
      <div className="relative flex w-full">
        <Sidebar />
        <main
          className={cn(
            'relative min-h-screen flex-1 pt-14 lg:pt-0 transition-[margin] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]',
            collapsed ? 'lg:ml-20' : 'lg:ml-64'
          )}
        >
          {children}
        </main>
      </div>
    </>
  );
}
