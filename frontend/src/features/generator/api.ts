import type { ResumeDocumentPayload } from '@/features/shared/types';
import api from '@/lib/api';

export interface GenerateResumeParams {
  reference: File;
  profile?: File;
  jobDescriptionFile?: File;
  jobText?: string;
  accentColor?: string;
  primaryColor?: string;
}

export async function generateResume({
  reference,
  profile,
  jobDescriptionFile,
  jobText,
  accentColor,
  primaryColor,
}: GenerateResumeParams): Promise<ResumeDocumentPayload> {
  const formData = new FormData();
  formData.append('reference', reference);
  if (profile) {
    formData.append('profile', profile);
  }

  if (jobDescriptionFile) {
    formData.append('job_description', jobDescriptionFile);
  }

  if (jobText) {
    formData.append('job_text', jobText);
  }

  if (accentColor) {
    formData.append('accent_color', accentColor);
  }

  if (primaryColor) {
    formData.append('primary_color', primaryColor);
  }

  const { data } = await api.post<ResumeDocumentPayload>('/api/generate', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function updateResume(
  resumeId: string,
  payload: { sections: unknown[] },
): Promise<ResumeDocumentPayload> {
  const { data } = await api.put<ResumeDocumentPayload>('/api/resume/' + resumeId, payload);
  return data;
}

const DEFAULT_DOWNLOAD_NAME = 'Khajamastan-Bellamkonda.pdf';

export function buildDownloadName(_profileName?: string) {
  return DEFAULT_DOWNLOAD_NAME;
}
