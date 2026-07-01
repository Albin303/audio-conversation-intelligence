'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useState } from 'react';
import { NAV_ITEMS, scrollToSection } from '@/config/navigation';
import { cn } from '@/lib/utils';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { useSidebar } from '@/providers/SidebarContext';

const STAT_CARDS = [
  {
    icon: '🎙️',
    title: 'Whisper ASR',
    value: '99.2%',
    sub: 'Transcription accuracy',
    accent: 'from-blue-500/20 to-blue-500/5',
    dot: 'bg-blue-500',
  },
  {
    icon: '👥',
    title: 'Speaker ID',
    value: 'Auto',
    sub: 'Agent & customer split',
    accent: 'from-violet-500/20 to-violet-500/5',
    dot: 'bg-violet-500',
  },
  {
    icon: '⚡',
    title: 'Low Latency',
    value: '< 2s',
    sub: 'Real-time pipeline',
    accent: 'from-emerald-500/20 to-emerald-500/5',
    dot: 'bg-emerald-500',
  },
];

export function Sidebar() {
  const { collapsed, toggle } = useSidebar();
  const [activeSection, setActiveSection] = useState('hero');
  const [cardIndex, setCardIndex] = useState(0);
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  useEffect(() => {
    const handleScroll = () => {
      const scrollPosition = window.scrollY + window.innerHeight / 3;
      for (const item of NAV_ITEMS) {
        const section = document.getElementById(item.id);
        if (
          section &&
          section.offsetTop <= scrollPosition &&
          section.offsetTop + section.offsetHeight > scrollPosition
        ) {
          setActiveSection(item.id);
        }
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Auto-cycle cards every 3 seconds
  useEffect(() => {
    if (collapsed) return;
    const timer = setInterval(() => {
      setCardIndex((prev) => (prev + 1) % STAT_CARDS.length);
    }, 3000);
    return () => clearInterval(timer);
  }, [collapsed]);

  const card = STAT_CARDS[cardIndex];

  return (
    <motion.aside
      initial={{ x: -24, opacity: 0, width: collapsed ? 80 : 256 }}
      animate={{ x: 0, opacity: 1, width: collapsed ? 80 : 256 }}
      transition={{ 
        width: { duration: 0.3, ease: [0.16, 1, 0.3, 1] }, 
        default: { duration: 0.6, ease: [0.16, 1, 0.3, 1] } 
      }}
      className="fixed left-0 top-0 z-40 hidden h-screen flex-col border-r border-nexus-border bg-nexus-bg/80 px-4 py-6 backdrop-blur-xl lg:flex overflow-hidden"
    >
      <div className={cn("mb-6 flex items-center px-2 shrink-0", collapsed ? "flex-col gap-4" : "justify-between gap-3")}>
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-nexus-accent text-sm font-bold text-white shadow-soft">
            S
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <div className="text-xs font-semibold tracking-tight text-nexus-fg leading-snug break-words max-w-[150px]">
                Speech Intelligence and Intent Detection
              </div>
              <div className="text-[10px] uppercase tracking-[0.18em] text-nexus-muted">
                Audio Intelligence
              </div>
            </div>
          )}
        </div>
        
        {/* Toggle Button */}
        <button
          type="button"
          onClick={toggle}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-nexus-border text-nexus-muted hover:text-nexus-fg hover:bg-nexus-card transition-colors duration-200"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <span className="text-xs font-mono font-bold leading-none">&gt;|</span>
          ) : (
            <span className="text-xs font-mono font-bold leading-none">&lt;|</span>
          )}
        </button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        {!collapsed && (
          <p className="mb-3 px-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-nexus-muted shrink-0">
            Navigation
          </p>
        )}

        <nav className="no-scrollbar flex flex-1 flex-col gap-1 overflow-y-auto pr-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;

            return (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  scrollToSection(item.id);
                  setActiveSection(item.id);
                }}
                onMouseEnter={() => collapsed && setHoveredItem(item.id)}
                onMouseLeave={() => setHoveredItem(null)}
                className={cn(
                  'group relative flex items-center rounded-xl transition-all duration-200 ease-in-out',
                  collapsed ? 'justify-center h-10 w-10 mx-auto px-0' : 'px-3 py-2.5 gap-3 w-full',
                  isActive
                    ? 'bg-nexus-accent/10 text-nexus-accent font-semibold'
                    : 'text-nexus-muted hover:bg-nexus-card hover:text-nexus-fg',
                )}
                style={{
                  boxShadow: isActive ? 'inset 3px 0px 0px rgb(var(--nexus-accent))' : undefined
                }}
              >
                <Icon 
                  className={cn(
                    "h-4 w-4 transition-transform duration-200 ease-in-out shrink-0",
                    isActive ? "rotate-[5deg]" : "group-hover:scale-[1.02]"
                  )} 
                  strokeWidth={isActive ? 2.4 : 2} 
                />
                {!collapsed && <span className="flex-1 text-left truncate">{item.label}</span>}
                {!collapsed && isActive && (
                  <span className="h-1.5 w-1.5 rounded-full bg-nexus-accent" />
                )}

                {/* Tooltip on hover when collapsed */}
                {collapsed && hoveredItem === item.id && (
                  <div className="absolute left-16 z-50 rounded-lg bg-slate-900 dark:bg-slate-950 px-3 py-1.5 text-xs text-white border border-nexus-border shadow-lg pointer-events-none whitespace-nowrap animate-scale-in">
                    {item.label}
                  </div>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      <div className="mt-4 space-y-3 px-1 shrink-0">
        <ThemeToggle className="w-full justify-center" compact={collapsed} />

        {!collapsed && (
          <>
            {/* Auto-sliding feature stat card */}
            <div className="relative overflow-hidden rounded-2xl border border-nexus-border bg-nexus-card h-[90px]">
              <AnimatePresence mode="wait">
                <motion.div
                  key={cardIndex}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -16 }}
                  transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                  className={`absolute inset-0 bg-gradient-to-br ${card.accent} p-4 flex flex-col justify-between`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-base leading-none">{card.icon}</span>
                    <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-nexus-muted">{card.title}</span>
                    <div className={`h-2 w-2 rounded-full ${card.dot} animate-pulse`} />
                  </div>
                  <div>
                    <p className="text-xl font-bold text-nexus-fg">{card.value}</p>
                    <p className="text-[11px] text-nexus-muted mt-0.5">{card.sub}</p>
                  </div>
                </motion.div>
              </AnimatePresence>

              {/* Dot indicators */}
              <div className="absolute bottom-2 right-3 flex gap-1">
                {STAT_CARDS.map((_, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setCardIndex(i)}
                    className={cn(
                      'h-1.5 rounded-full transition-all duration-300',
                      i === cardIndex ? 'w-4 bg-nexus-accent' : 'w-1.5 bg-nexus-border',
                    )}
                  />
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-nexus-border bg-nexus-card p-4 animate-scale-in">
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-nexus-muted">
                Platform
              </p>
              <p className="mt-2 text-sm font-medium text-nexus-fg">Enterprise audio pipeline</p>
              <p className="mt-1 text-xs leading-relaxed text-nexus-muted">
                Whisper · LLaMA · XGBoost
              </p>
            </div>
          </>
        )}
      </div>
    </motion.aside>
  );
}
