/**
 * TanStack Query hooks for Learning Loop reports.
 *
 * - useLearningReport() — fetches latest report (5min stale time)
 * - useLearningReports() — list with date filters
 * - useTriggerAnalysis() — mutation for POST /trigger
 *
 * Sprint 28, Session 6a.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getLearningReports,
  getLearningReport,
  triggerLearningAnalysis,
} from '../api/learningApi';
import type {
  ReportsListResponse,
  ReportDetailResponse,
  TriggerResponse,
} from '../api/learningApi';

/**
 * Fetch the latest learning report.
 *
 * Gets the most recent report from the list endpoint (limit=1),
 * then fetches full detail. 5-minute stale time.
 */
export function useLearningReport() {
  const latestList = useQuery<ReportsListResponse, Error>({
    queryKey: ['learning', 'reports', 'latest'],
    queryFn: () => getLearningReports({ limit: 1 }),
    staleTime: 5 * 60 * 1000,
  });

  const latestReportId = latestList.data?.reports[0]?.report_id;

  const detail = useQuery<ReportDetailResponse, Error>({
    queryKey: ['learning', 'report', latestReportId],
    queryFn: () => getLearningReport(latestReportId!),
    enabled: Boolean(latestReportId),
    staleTime: 5 * 60 * 1000,
  });

  return {
    report: detail.data?.report ?? null,
    isLoading: latestList.isLoading || (latestList.isSuccess && detail.isLoading),
    isError: latestList.isError || detail.isError,
    error: latestList.error ?? detail.error,
  };
}

/**
 * Fetch learning reports with optional date filters.
 */
export function useLearningReports(startDate?: string, endDate?: string) {
  return useQuery<ReportsListResponse, Error>({
    queryKey: ['learning', 'reports', { startDate, endDate }],
    queryFn: () =>
      getLearningReports({
        start_date: startDate,
        end_date: endDate,
      }),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Mutation hook to trigger a learning analysis run.
 *
 * Invalidates reports and proposals queries on success.
 */
export function useTriggerAnalysis() {
  const queryClient = useQueryClient();

  return useMutation<TriggerResponse, Error>({
    mutationFn: triggerLearningAnalysis,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['learning', 'reports'] });
      queryClient.invalidateQueries({ queryKey: ['learning', 'report'] });
      queryClient.invalidateQueries({ queryKey: ['learning', 'proposals'] });
    },
  });
}
