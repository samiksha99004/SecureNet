/**
 * SecureNet — Model Service
 *
 * Fetches ML model information (Isolation Forest + XGBoost).
 *
 * TODO (backend): Connect all endpoints once the API is ready.
 */

import { apiClient } from './apiClient';
import type { ModelInfo, FeatureImportance } from '../types/model.types';

/** TODO (backend): GET /model/info */
export async function getModelInfo(): Promise<ModelInfo> {
  return apiClient.get<ModelInfo>('/model/info');
}

/** TODO (backend): GET /model/feature-importance?stage=1|2&limit=N */
export async function getFeatureImportance(
  stage: 1 | 2,
  limit = 20
): Promise<FeatureImportance[]> {
  return apiClient.get<FeatureImportance[]>(
    `/model/feature-importance?stage=${stage}&limit=${limit}`
  );
}
