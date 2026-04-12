import type { ResumeDocumentPayload, ResumeProfile } from '@/features/shared/types';
import api from '@/lib/api';

export interface SampleProfileSummary {
  id: string;
  label: string;
}

interface SampleProfilesResponse {
  default_profile: string;
  profiles: SampleProfileSummary[];
}

export const defaultSampleProfileId = 'Khaja';

export interface GenerateResumeParams {
  reference?: File;
  profile?: File;
  jobDescriptionFile?: File;
  jobText?: string;
  sampleProfile?: string;
  accentColor?: string;
  primaryColor?: string;
}

export async function generateResume({
  reference,
  profile,
  jobDescriptionFile,
  jobText,
  sampleProfile,
  accentColor,
  primaryColor,
}: GenerateResumeParams = {}): Promise<ResumeDocumentPayload> {
  const formData = new FormData();
  if (reference) {
    formData.append('reference', reference);
  }
  if (profile) {
    formData.append('profile', profile);
  }

  if (jobDescriptionFile) {
    formData.append('job_description', jobDescriptionFile);
  }

  if (jobText) {
    formData.append('job_text', jobText);
  }

  if (sampleProfile) {
    formData.append('sample_profile', sampleProfile);
  }

  if (accentColor) {
    formData.append('accent_color', accentColor);
  }

  if (primaryColor) {
    formData.append('primary_color', primaryColor);
  }

  const { data } = await api.post<ResumeDocumentPayload>('/api/generate', formData);
  return data;
}

export async function fetchSampleProfiles(): Promise<SampleProfilesResponse> {
  const { data } = await api.get<SampleProfilesResponse>('/api/sample-profiles');
  return data;
}

export async function updateResume(
  resumeId: string,
  payload: { sections: unknown[]; profile?: ResumeProfile; theme?: Record<string, unknown> },
): Promise<ResumeDocumentPayload> {
  const { data } = await api.put<ResumeDocumentPayload>('/api/resume/' + resumeId, payload);
  return data;
}

const DEFAULT_DOWNLOAD_NAME = 'Khajamastan-Bellamkonda.pdf';

export function buildDownloadName(_profileName?: string) {
  return DEFAULT_DOWNLOAD_NAME;
}
