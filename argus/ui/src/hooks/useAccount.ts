/**
 * TanStack Query hook for account data.
 *
 * Fetches account info (equity, cash, buying power, daily P&L) with 5s polling.
 * Position prices update in real-time via WebSocket; this polling refreshes
 * the account-level summary from the broker.
 */

import { useQuery } from '@tanstack/react-query';
import { getAccount } from '../api/client';
import type { AccountResponse } from '../api/types';

export function useAccount() {
  return useQuery<AccountResponse, Error>({
    queryKey: ['account'],
    queryFn: getAccount,
    refetchInterval: 5_000, // 5 seconds
  });
}
