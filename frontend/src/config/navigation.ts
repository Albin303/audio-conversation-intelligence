import type { LucideIcon } from 'lucide-react';
import {
  Home,
  UploadCloud,
  FileText,
  BrainCircuit,
  LineChart,
  Bell,
  Settings,
  Sparkles,
  Activity,
} from 'lucide-react';

export type NavItem = {
  id: string;
  label: string;
  icon: LucideIcon;
  hint?: string;
};

export const NAV_ITEMS: NavItem[] = [
  { id: 'hero', label: 'Home', icon: Home, hint: 'Return to top' },
  { id: 'live-stream', label: 'Live Stream Capture', icon: Activity, hint: 'Record speech' },
  { id: 'upload', label: 'Upload Audio', icon: UploadCloud, hint: 'Import audio' },
  { id: 'input', label: 'Conversation', icon: FileText, hint: 'Speech transcript' },
  { id: 'extraction', label: 'Feature Extraction', icon: BrainCircuit, hint: 'Signals & PII' },
  { id: 'prediction', label: 'Prediction', icon: LineChart, hint: 'Lead scoring' },
  { id: 'follow-up-alerts', label: 'Follow-Up Alerts', icon: Bell, hint: 'Action items' },
  { id: 'benefits', label: 'Key Benefits', icon: Sparkles, hint: 'Key benefits' },
  { id: 'settings', label: 'Settings', icon: Settings, hint: 'System settings' },
];

export const TARGET_NAV_ITEMS = NAV_ITEMS;

export function scrollToSection(id: string) {
  const element = document.getElementById(id);
  if (!element) return;
  element.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
