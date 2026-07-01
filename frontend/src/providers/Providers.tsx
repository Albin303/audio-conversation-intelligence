'use client';

import { SmoothScrollProvider } from '@/providers/SmoothScrollProvider';
import { ThemeProvider } from '@/providers/ThemeProvider';
import { SidebarProvider } from '@/providers/SidebarContext';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <SidebarProvider>
        <SmoothScrollProvider>{children}</SmoothScrollProvider>
      </SidebarProvider>
    </ThemeProvider>
  );
}
