/**
 * Hook to extract intelligence pipeline active status from the health endpoint.
 *
 * Returns a boolean indicating whether the catalyst/intelligence pipeline is
 * running. Used to gate TanStack Query hooks that would otherwise fire
 * requests to endpoints that return 503 when the pipeline is disabled.
 *
 * Fail-closed: returns false if health endpoint fails or is loading.
 *
 * Sprint 23.9 Session 1 — DEC-329
 */

import { useHealth } from './useHealth';

/**
 * Check if the intelligence pipeline is active via the health endpoint.
 *
 * Looks for a 'catalyst_pipeline' component in the health response.
 * When present and healthy, the pipeline is active.
 *
 * @returns Whether the intelligence pipeline is active (fail-closed to false)
 */
export function usePipelineStatus(): boolean {
  const { data, isSuccess } = useHealth();

  if (!isSuccess || !data?.components) {
    return false;
  }

  const pipelineComponent = data.components['catalyst_pipeline'];
  return pipelineComponent?.status === 'healthy';
}
