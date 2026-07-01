'use client';

import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Bell, CalendarDays, CheckCircle2, Clock3, Filter, Loader2, Rows3, Search, UserRound, Sparkles, ListChecks } from 'lucide-react';
import { apiService, FollowUpAlert } from '@/services/api';
import { useAppStore } from '@/store/useAppStore';
import { cn } from '@/lib/utils';

const priorities = [
  { value: 'All', label: 'Any priority' },
  { value: 'High', label: 'High' },
  { value: 'Medium', label: 'Medium' },
  { value: 'Low', label: 'Low' },
];
const statuses = [
  { value: 'All', label: 'Any status' },
  { value: 'Pending', label: 'Pending' },
  { value: 'Completed', label: 'Completed' },
];
const dateFilters = [
  { value: 'All', label: 'Any date' },
  { value: 'Today', label: 'Today' },
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
];
const rowOptions = ['5', '10', '25', 'All'];

const priorityClass: Record<string, string> = {
  High: 'bg-rose-500/10 text-rose-600 border-rose-500/25 dark:text-rose-400',
  Medium: 'bg-amber-500/10 text-amber-600 border-amber-500/25 dark:text-amber-400',
  Low: 'bg-emerald-500/10 text-emerald-600 border-emerald-500/25 dark:text-emerald-400',
};

function formatDate(value: string) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function StatusBadge({ status }: { status: FollowUpAlert['status'] }) {
  const isPending = status === 'Pending';
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-bold',
        isPending
          ? 'border-ai-blue/25 bg-ai-blue/10 text-ai-blue dark:text-ai-blue-light'
          : 'border-ai-emerald/25 bg-ai-emerald/10 text-ai-emerald'
      )}
    >
      {isPending ? <Clock3 className="h-3 w-3" /> : <CheckCircle2 className="h-3 w-3" />}
      {status}
    </span>
  );
}

function PriorityBadge({ priority }: { priority: FollowUpAlert['priority'] }) {
  return (
    <span className={cn('inline-flex rounded-full border px-2.5 py-1 text-[11px] font-bold tracking-wide', priorityClass[priority])}>
      {priority}
    </span>
  );
}

function isWithinDateFilter(value: string, filter: string) {
  if (filter === 'All') return true;
  const created = new Date(value);
  if (Number.isNaN(created.getTime())) return false;

  const now = new Date();
  if (filter === 'Today') {
    return created.toDateString() === now.toDateString();
  }

  const days = filter === '7d' ? 7 : 30;
  const cutoff = new Date(now);
  cutoff.setDate(now.getDate() - days);
  return created >= cutoff;
}

function ExpandableText({ text, quoted = false, maxChars = 110 }: { text: string; quoted?: boolean; maxChars?: number }) {
  const [isOpen, setIsOpen] = useState(false);
  const cleanText = text || '-';
  const needsToggle = cleanText.length > maxChars;
  const visibleText = !needsToggle || isOpen ? cleanText : `${cleanText.slice(0, maxChars).trim()}...`;

  return (
    <div>
      <p className={cn('text-sm leading-6', quoted ? 'text-gray-600 dark:text-gray-300 italic' : 'text-gray-700 dark:text-gray-200')}>
        {quoted ? `"${visibleText}"` : visibleText}
      </p>
      {needsToggle && (
        <button
          onClick={() => setIsOpen((current) => !current)}
          className="mt-1 text-[11px] font-bold text-ai-blue hover:text-ai-indigo dark:text-ai-blue-light transition-colors"
        >
          {isOpen ? 'Show less' : 'Show more'}
        </button>
      )}
    </div>
  );
}

function FilterPillGroup<T extends string>({
  options, value, onChange, activeClass = 'border-ai-blue bg-gradient-to-br from-ai-blue to-ai-indigo text-white shadow-glow-blue'
}: {
  options: { value: T; label: string }[]; value: T; onChange: (v: T) => void; activeClass?: string;
}) {
  return (
    <div className="inline-flex items-center gap-1 p-1 rounded-xl bg-gray-100/60 dark:bg-white/[0.03] border border-gray-200/60 dark:border-white/5">
      {options.map((item) => {
        const isActive = value === item.value;
        return (
          <button
            key={item.value}
            onClick={() => onChange(item.value)}
            className={cn(
              'relative px-3 py-1.5 text-[11px] font-bold rounded-lg transition-all duration-300 ease-expo-out',
              isActive
                ? activeClass
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            )}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}

export function FollowUpAlertsSection() {
  const followUpRefreshKey = useAppStore((state) => state.followUpRefreshKey);
  const refreshFollowUpAlerts = useAppStore((state) => state.refreshFollowUpAlerts);
  const [alerts, setAlerts] = useState<FollowUpAlert[]>([]);
  const [priority, setPriority] = useState('All');
  const [status, setStatus] = useState('Pending');
  const [dateFilter, setDateFilter] = useState('All');
  const [rowsPerPage, setRowsPerPage] = useState('10');
  const [customerName, setCustomerName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const filteredAlerts = useMemo(
    () => alerts.filter((alert) => isWithinDateFilter(alert.created_date, dateFilter)),
    [alerts, dateFilter]
  );
  const visibleAlerts = useMemo(
    () => rowsPerPage === 'All' ? filteredAlerts : filteredAlerts.slice(0, Number(rowsPerPage)),
    [filteredAlerts, rowsPerPage]
  );
  const activeCount = useMemo(() => filteredAlerts.filter((alert) => alert.status === 'Pending').length, [filteredAlerts]);
  const completedCount = useMemo(() => filteredAlerts.filter((alert) => alert.status === 'Completed').length, [filteredAlerts]);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    apiService
      .getFollowUpAlerts({
        priority: priority === 'All' ? undefined : priority,
        status: status === 'All' ? undefined : status,
        customerName: customerName.trim() || undefined,
      })
      .then((items) => {
        if (isMounted) setAlerts(items);
      })
      .catch((error) => {
        console.error('Failed to load follow-up alerts', error);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [priority, status, customerName, followUpRefreshKey]);

  const completeAlert = async (alertId: string) => {
    setUpdatingId(alertId);
    try {
      await apiService.updateFollowUpStatus(alertId, 'Completed');
      refreshFollowUpAlerts();
    } catch (error) {
      console.error('Failed to complete follow-up alert', error);
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <section id="follow-up-alerts" className="py-24 md:py-28 px-4 sm:px-8 relative max-w-7xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: '-100px' }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        className="mb-10 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between"
      >
        <div>
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="mb-5 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-ai-blue/15 to-ai-cyan/10 shadow-glow-blue relative"
          >
            <Bell className="h-6 w-6 text-ai-blue" strokeWidth={2.2} />
            <div className="absolute inset-0 rounded-2xl ring-1 ring-ai-blue/20" />
            <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-gradient-to-br from-ai-rose to-ai-amber shadow-[0_0_12px_rgba(244,63,94,0.6)] ring-2 ring-white dark:ring-gray-950" />
          </motion.div>
          <h2 className="text-3xl md:text-5xl font-bold text-gray-900 dark:text-white tracking-tight">
            <span className="mr-1">🔔</span>
            <span className="gradient-text-cool">Follow-Up Alerts</span>
          </h2>
          <p className="mt-3 max-w-2xl text-gray-500 dark:text-gray-400 text-pretty">
            Customer commitments, callbacks, demos, proposals, clarifications, and deferred decisions captured as CRM tasks.
          </p>
        </div>

        <div className="grid grid-cols-3 gap-2.5">
          {[
            { label: 'Pending', value: activeCount, gradient: 'from-ai-blue to-ai-indigo', icon: Clock3 },
            { label: 'Completed', value: completedCount, gradient: 'from-ai-emerald to-ai-cyan', icon: CheckCircle2 },
            { label: 'Total', value: filteredAlerts.length, gradient: 'from-ai-purple to-ai-rose', icon: ListChecks },
          ].map((stat) => {
            const Icon = stat.icon;
            return (
              <div key={stat.label} className="relative group surface-elevated rounded-2xl px-4 py-3 overflow-hidden min-w-[110px]">
                <div className={`absolute -top-10 -right-10 w-24 h-24 bg-gradient-to-br ${stat.gradient} opacity-15 rounded-full blur-2xl group-hover:opacity-30 transition-opacity`} aria-hidden />
                <div className={`absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r ${stat.gradient}`} />
                <div className="relative flex items-center gap-1.5 mb-1">
                  <Icon className="w-3 h-3 text-gray-400" />
                  <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">{stat.label}</span>
                </div>
                <strong className="text-2xl text-gray-900 dark:text-white font-black tracking-tight">{stat.value}</strong>
              </div>
            );
          })}
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: '-50px' }}
        transition={{ duration: 0.7, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
        className="mb-5 surface-elevated rounded-2xl p-3"
      >
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:flex-wrap">
          <label className="relative flex items-center flex-1 min-w-[200px]">
            <Search className="pointer-events-none absolute left-3.5 h-4 w-4 text-gray-400" />
            <input
              value={customerName}
              onChange={(event) => setCustomerName(event.target.value)}
              placeholder="Filter customer by name or company..."
              className="h-11 w-full rounded-xl border border-gray-200/60 dark:border-white/5 bg-white/60 dark:bg-white/[0.02] pl-10 pr-3 text-sm text-gray-900 outline-none transition focus:border-ai-blue focus:ring-2 focus:ring-ai-blue/20 dark:text-white"
            />
          </label>

          <div className="flex items-center gap-2 flex-wrap">
            <Filter className="h-3.5 w-3.5 text-gray-400 shrink-0" />
            <FilterPillGroup options={priorities as any} value={priority} onChange={setPriority as any} />
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <FilterPillGroup
              options={statuses as any}
              value={status}
              onChange={setStatus as any}
              activeClass="border-gray-900 bg-gradient-to-br from-gray-900 to-gray-700 text-white shadow-soft dark:border-white dark:from-white dark:to-gray-200 dark:text-gray-900"
            />
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <label className="relative flex items-center">
              <CalendarDays className="pointer-events-none absolute left-3 h-4 w-4 text-gray-400" />
              <select
                value={dateFilter}
                onChange={(event) => setDateFilter(event.target.value)}
                className="h-10 min-w-[150px] appearance-none rounded-xl border border-gray-200/60 dark:border-white/5 bg-white/60 dark:bg-white/[0.02] pl-10 pr-8 text-[11px] font-bold text-gray-700 outline-none transition focus:border-ai-blue focus:ring-2 focus:ring-ai-blue/20 dark:text-gray-200"
              >
                {dateFilters.map((item) => (
                  <option key={item.value} value={item.value}>{item.label}</option>
                ))}
              </select>
            </label>

            <label className="relative flex items-center">
              <Rows3 className="pointer-events-none absolute left-3 h-4 w-4 text-gray-400" />
              <select
                value={rowsPerPage}
                onChange={(event) => setRowsPerPage(event.target.value)}
                className="h-10 min-w-[110px] appearance-none rounded-xl border border-gray-200/60 dark:border-white/5 bg-white/60 dark:bg-white/[0.02] pl-10 pr-8 text-[11px] font-bold text-gray-700 outline-none transition focus:border-ai-blue focus:ring-2 focus:ring-ai-blue/20 dark:text-gray-200"
              >
                {rowOptions.map((item) => (
                  <option key={item} value={item}>{item === 'All' ? 'All rows' : `${item} rows`}</option>
                ))}
              </select>
            </label>
          </div>
        </div>
      </motion.div>

      {!isLoading && filteredAlerts.length > 0 && (
        <p className="mb-3 text-sm text-gray-500 dark:text-gray-400 inline-flex items-center gap-2">
          <Sparkles className="w-3.5 h-3.5 text-ai-blue" />
          Showing {visibleAlerts.length} of {filteredAlerts.length} alert{filteredAlerts.length === 1 ? '' : 's'}
        </p>
      )}

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: '-50px' }}
        transition={{ duration: 0.7, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
        className="relative surface-elevated overflow-hidden"
      >
        {isLoading ? (
          <div className="flex h-72 items-center justify-center gap-3 text-gray-500">
            <div className="relative">
              <div className="absolute inset-0 rounded-full bg-ai-blue/20 blur-xl" />
              <Loader2 className="relative h-6 w-6 animate-spin text-ai-blue" />
            </div>
            <span className="text-sm font-semibold">Loading alert queue...</span>
          </div>
        ) : filteredAlerts.length === 0 ? (
          <div className="flex h-72 flex-col items-center justify-center gap-3 px-6 text-center text-gray-500">
            <div className="relative">
              <div className="absolute inset-0 rounded-full bg-gray-400/10 blur-xl" />
              <div className="relative w-14 h-14 rounded-2xl bg-gradient-to-br from-gray-100 to-white dark:from-white/5 dark:to-white/[0.02] flex items-center justify-center border border-dashed border-gray-300 dark:border-white/10">
                <Bell className="h-6 w-6 text-gray-300" strokeWidth={1.5} />
              </div>
            </div>
            <p className="text-sm font-semibold text-gray-700 dark:text-gray-300">No follow-up alerts</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Try adjusting your filters to see more results.</p>
          </div>
        ) : (
          <>
            <div className="hidden lg:block overflow-x-auto">
              <table className="w-full table-fixed">
                <thead className="bg-gradient-to-r from-gray-50/80 to-white/40 dark:from-white/[0.02] dark:to-transparent text-left">
                  <tr>
                    <th className="w-[12%] px-4 py-4 text-[10px] font-bold uppercase tracking-[0.18em] text-gray-500">Customer</th>
                    <th className="w-[12%] px-4 py-4 text-[10px] font-bold uppercase tracking-[0.18em] text-gray-500">Company</th>
                    <th className="w-[18%] px-4 py-4 text-[10px] font-bold uppercase tracking-[0.18em] text-gray-500">Action Needed</th>
                    <th className="w-[8%] px-4 py-4 text-[10px] font-bold uppercase tracking-[0.18em] text-gray-500">Priority</th>
                    <th className="w-[17%] px-4 py-4 text-[10px] font-bold uppercase tracking-[0.18em] text-gray-500">Reason</th>
                    <th className="w-[18%] px-4 py-4 text-[10px] font-bold uppercase tracking-[0.18em] text-gray-500">Source Statement</th>
                    <th className="w-[10%] px-4 py-4 text-[10px] font-bold uppercase tracking-[0.18em] text-gray-500">Created</th>
                    <th className="w-[10%] px-4 py-4 text-[10px] font-bold uppercase tracking-[0.18em] text-gray-500">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-white/5">
                  {visibleAlerts.map((alert, idx) => (
                    <motion.tr
                      key={alert.id}
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.4, delay: idx * 0.03 }}
                      className="align-top transition-all duration-300 hover:bg-gradient-to-r hover:from-ai-blue/[0.04] hover:to-transparent dark:hover:from-ai-blue/[0.06]"
                    >
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-2 font-semibold text-gray-900 dark:text-white">
                          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-ai-blue/20 to-ai-purple/10 flex items-center justify-center text-[10px] font-bold text-ai-blue">
                            {(alert.customer_name || '?').charAt(0).toUpperCase()}
                          </div>
                          <span className="truncate">{alert.customer_name || 'Unknown'}</span>
                        </div>
                      </td>
                      <td className="px-4 py-4 text-sm text-gray-600 dark:text-gray-300">{alert.company_name || '-'}</td>
                      <td className="px-4 py-4 text-sm font-semibold text-gray-900 dark:text-white">
                        <ExpandableText text={alert.action_needed} maxChars={85} />
                      </td>
                      <td className="px-4 py-4"><PriorityBadge priority={alert.priority} /></td>
                      <td className="px-4 py-4"><ExpandableText text={alert.reason} maxChars={95} /></td>
                      <td className="px-4 py-4"><ExpandableText text={alert.source_text} quoted maxChars={100} /></td>
                      <td className="px-4 py-4 text-xs text-gray-500 dark:text-gray-400 font-mono">{formatDate(alert.created_date)}</td>
                      <td className="px-4 py-4">
                        <div className="flex flex-col items-start gap-2">
                          <StatusBadge status={alert.status} />
                          {alert.status === 'Pending' && (
                            <button
                              onClick={() => completeAlert(alert.id)}
                              disabled={updatingId === alert.id}
                              className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-gradient-to-br from-ai-emerald to-ai-cyan px-2.5 text-[11px] font-bold text-white transition-all duration-300 ease-expo-out hover:-translate-y-0.5 hover:shadow-glow-cyan disabled:opacity-60 disabled:hover:translate-y-0"
                            >
                              {updatingId === alert.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <CheckCircle2 className="h-3 w-3" />}
                              Complete
                            </button>
                          )}
                        </div>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="grid gap-3 p-3 lg:hidden">
              {visibleAlerts.map((alert, idx) => (
                <motion.article
                  key={alert.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: idx * 0.04 }}
                  className="relative surface-elevated rounded-2xl p-4 overflow-hidden"
                >
                  <div className={`absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r ${
                    alert.priority === 'High' ? 'from-rose-500 to-amber-500' :
                    alert.priority === 'Medium' ? 'from-amber-500 to-amber-300' : 'from-emerald-500 to-cyan-500'
                  }`} />
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-9 h-9 rounded-full bg-gradient-to-br from-ai-blue/20 to-ai-purple/10 flex items-center justify-center text-xs font-bold text-ai-blue">
                        {(alert.customer_name || '?').charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="text-sm font-bold text-gray-900 dark:text-white">{alert.customer_name || 'Unknown Customer'}</p>
                        <p className="text-[11px] text-gray-500">{alert.company_name || 'No company captured'}</p>
                      </div>
                    </div>
                    <PriorityBadge priority={alert.priority} />
                  </div>
                  <div className="mb-2 font-semibold text-gray-900 dark:text-white">
                    <ExpandableText text={alert.action_needed} maxChars={90} />
                  </div>
                  <div className="mb-3">
                    <ExpandableText text={alert.reason} maxChars={120} />
                  </div>
                  <div className="mb-4 rounded-xl bg-gray-50/80 dark:bg-white/[0.02] p-3 border border-gray-200/40 dark:border-white/5">
                    <ExpandableText text={alert.source_text} quoted maxChars={130} />
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <span className="text-[11px] text-gray-500 font-mono">{formatDate(alert.created_date)}</span>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={alert.status} />
                      {alert.status === 'Pending' && (
                        <button
                          onClick={() => completeAlert(alert.id)}
                          disabled={updatingId === alert.id}
                          className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-gradient-to-br from-ai-emerald to-ai-cyan px-3 text-[11px] font-bold text-white transition-all duration-300 ease-expo-out hover:-translate-y-0.5 disabled:opacity-60"
                        >
                          {updatingId === alert.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <CheckCircle2 className="h-3 w-3" />}
                          Complete
                        </button>
                      )}
                    </div>
                  </div>
                </motion.article>
              ))}
            </div>
          </>
        )}
      </motion.div>
    </section>
  );
}
