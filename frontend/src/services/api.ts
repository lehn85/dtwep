import { CaseDetail, CaseSummary, ConfigInfo, ResultsData } from '../types';

export const API_BASE = (import.meta.env.VITE_API_BASE_URL as string) || '/api';

export async function fetchCases(): Promise<CaseSummary[]> {
  const res = await fetch(`${API_BASE}/cases`);
  if (!res.ok) throw new Error('Failed to fetch cases list');
  const data = await res.json();
  return data.cases || [];
}

export async function fetchCaseDetail(caseId: string): Promise<CaseDetail> {
  const res = await fetch(`${API_BASE}/cases/${caseId}`);
  if (!res.ok) throw new Error(`Failed to fetch case detail for ${caseId}`);
  return res.json();
}

export async function fetchConfig(caseId: string, configName: string): Promise<ConfigInfo> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/configs/${configName}`);
  if (!res.ok) throw new Error(`Failed to fetch config ${configName}`);
  return res.json();
}

export async function saveConfig(caseId: string, configName: string, yamlContent: string): Promise<{ success: boolean; message?: string }> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/configs/${configName}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ yaml_content: yamlContent }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to save configuration');
  return data;
}

export async function fetchResults(caseId: string, expId: string): Promise<ResultsData> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/results/${expId}`);
  if (!res.ok) throw new Error(`Failed to fetch results for ${expId}`);
  return res.json();
}

export async function stopProcesses(caseId: string): Promise<{ success: boolean }> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/stop`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to stop processes');
  return res.json();
}
