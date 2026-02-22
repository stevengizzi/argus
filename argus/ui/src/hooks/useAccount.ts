/**
 * TanStack Query hook for account data.
 *
 * Fetches account info (equity, cash, buying power, daily P&L) with 10s polling.
 */

import { useQuery } from '@tanstack/react-query';
import { getAccount } from '../api/client';
import type { AccountResponse } from '../api/types';

export function useAccount() {
  return useQuery<AccountResponse, Error>({
    queryKey: ['account'],
    queryFn: getAccount,
    refetchInterval: 10_000, // 10 seconds
  });
}
