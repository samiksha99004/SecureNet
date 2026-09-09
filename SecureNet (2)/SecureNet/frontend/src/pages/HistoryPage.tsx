/**
 * SecureNet — History Page
 *
 * Complete security event history with:
 *  - Summary cards (total / severity counts)
 *  - Filter toolbar (search, severity, state, mode, protocol)
 *  - Sortable event table
 *  - Pagination
 *  - Incident Details Drawer (with resolve / false-positive actions)
 *  - CSV / PDF export (shows "Export not available" when backend is absent)
 *
 * Data fetched via eventsService → useAsyncData.
 * All filter/pagination state managed by useEventFilters.
 * No hardcoded security data.
 */

import { useCallback, useState } from 'react';
import { MainLayout } from '../components/layout/MainLayout';
import { PageHeader } from '../components/common/PageHeader';
import { Pagination } from '../components/common/Pagination';
import { HistoryFilters } from '../components/history/HistoryFilters';
import { HistorySummaryCards } from '../components/history/HistorySummaryCards';
import { EventsTable } from '../components/history/EventsTable';
import { IncidentDetailsDrawer } from '../components/history/IncidentDetailsDrawer';
import { ExportButton } from '../components/history/ExportButton';
import { useEventFilters } from '../hooks/useEventFilters';
import { useAsyncData } from '../hooks/useAsyncData';
import { useToast } from '../components/common/Toast';
import { getEvents, resolveEvent, markFalsePositive } from '../services/eventsService';
import type { SecurityEvent } from '../types/security.types';
import type { EventFilterParams } from '../types/api.types';
import styles from './HistoryPage.module.css';

/** Build a query string from the current filters for export URLs. */
function buildExportQS(filters: Partial<EventFilterParams>): string {
  const entries = Object.entries(filters).filter(
    ([, v]) => v !== null && v !== undefined && v !== ''
  );
  return new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString();
}

export function HistoryPage() {
  const {
    filters,
    setSearch,
    setFilter,
    setPage,
    setSort,
    resetFilters,
    hasActiveFilters,
  } = useEventFilters();

  const [selectedEvent, setSelectedEvent] = useState<SecurityEvent | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { showToast } = useToast();

  // Fetch events whenever filters change
  const fetcher = useCallback(
    () => getEvents(filters),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [JSON.stringify(filters)]
  );

  const { data, isLoading, isError, refetch } = useAsyncData(fetcher);

  const handleRowClick = useCallback((event: SecurityEvent) => {
    setSelectedEvent(event);
    setDrawerOpen(true);
  }, []);

  const handleCloseDrawer = useCallback(() => {
    setDrawerOpen(false);
  }, []);

  // ── Resolve / False-positive ──────────────────────────────────────────────

  const handleResolve = useCallback(async (id: string) => {
    try {
      await resolveEvent(id);
      showToast({ message: 'Event marked as resolved.', variant: 'success' });
      void refetch();
      // Update the selected event state optimistically
      setSelectedEvent((prev) =>
        prev && prev.id === id ? { ...prev, state: 'resolved' } : prev
      );
    } catch {
      showToast({ message: 'Could not resolve event — backend not connected.', variant: 'error' });
    }
  }, [refetch, showToast]);

  const handleMarkFalsePositive = useCallback(async (id: string) => {
    try {
      await markFalsePositive(id);
      showToast({ message: 'Event marked as false positive.', variant: 'success' });
      void refetch();
      setSelectedEvent((prev) =>
        prev && prev.id === id ? { ...prev, state: 'false_positive' } : prev
      );
    } catch {
      showToast({ message: 'Could not update event — backend not connected.', variant: 'error' });
    }
  }, [refetch, showToast]);

  const exportQS = buildExportQS(filters);

  return (
    <MainLayout title="Event History">
      <div className={styles.page}>
        <PageHeader
          title="Event History"
          description="Browse and investigate all detected security events."
          actions={
            <ExportButton
              queryString={exportQS}
              totalEvents={data?.total ?? null}
              disabled={isLoading || isError}
            />
          }
        />

        {/* Summary cards */}
        <HistorySummaryCards
          total={data?.total ?? null}
          isLoading={isLoading}
        />

        {/* Filters */}
        <HistoryFilters
          filters={filters}
          onSearch={setSearch}
          onFilter={setFilter}
          onReset={resetFilters}
          hasActiveFilters={hasActiveFilters}
        />

        {/* Results count */}
        {!isLoading && data && (
          <div className={styles.resultsInfo} aria-live="polite">
            <span className={styles.resultsCount}>
              {data.total.toLocaleString()} event{data.total !== 1 ? 's' : ''}
            </span>
            {hasActiveFilters && (
              <span className={styles.filterNote}>matching current filters</span>
            )}
          </div>
        )}

        {/* Events table */}
        <EventsTable
          events={data?.data ?? []}
          isLoading={isLoading}
          isError={isError}
          sortBy={filters.sortBy}
          sortOrder={filters.sortOrder}
          onSort={setSort}
          onRowClick={handleRowClick}
          onRetry={refetch}
        />

        {/* Pagination */}
        {data && data.totalPages > 1 && (
          <div className={styles.paginationRow}>
            <Pagination
              page={filters.page}
              totalPages={data.totalPages}
              onPageChange={setPage}
            />
            <span className={styles.pageInfo}>
              Page {filters.page} of {data.totalPages}
            </span>
          </div>
        )}
      </div>

      {/* Incident Details Drawer */}
      <IncidentDetailsDrawer
        event={selectedEvent}
        isOpen={drawerOpen}
        onClose={handleCloseDrawer}
        onResolve={handleResolve}
        onMarkFalsePositive={handleMarkFalsePositive}
      />
    </MainLayout>
  );
}
