import type { Metadata } from 'next';
import { Inter, Space_Grotesk, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { AppShell } from '@/components/layout/AppShell';
import { Providers } from '@/providers/Providers';
import { THEME_STORAGE_KEY } from '@/lib/theme';
import { SmoothScroll, CursorGlow } from '@/components/animations';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const spaceGrotesk = Space_Grotesk({
  variable: '--font-space-grotesk',
  subsets: ['latin'],
  weight: ['500', '600', '700'],
});

const geistSans = Inter({
  variable: '--font-geist-sans',
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700'],
});

const geistMono = JetBrains_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'Speech Intelligence and Intent Detection | Enterprise Audio Intelligence',
  description: 'Transform conversations into actionable insights.',
};

const themeInitScript = `
(function () {
  try {
    var key = '${THEME_STORAGE_KEY}';
    var stored = localStorage.getItem(key);
    var preference = stored === 'dark' || stored === 'light' || stored === 'system' ? stored : 'dark';
    var dark = preference === 'dark' || (preference === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
    var root = document.documentElement;
    root.classList.toggle('dark', dark);
    root.dataset.theme = dark ? 'dark' : 'light';
    root.style.colorScheme = dark ? 'dark' : 'light';
  } catch (e) {}
})();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${spaceGrotesk.variable} ${geistSans.variable} ${geistMono.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className={`${geistSans.className} min-h-screen bg-nexus-bg text-nexus-fg antialiased`}>
        <div className="noise-overlay" aria-hidden />
        <Providers>
          <SmoothScroll>
            <CursorGlow />
            <AppShell>{children}</AppShell>
          </SmoothScroll>
        </Providers>
      </body>
    </html>
  );
}
