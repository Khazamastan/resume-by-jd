import type { ResumeDocumentPayload } from '@/features/shared/types';
import api from '@/lib/api';

export interface GenerateResumeParams {
  reference: File;
  profile: File;
  jobDescriptionFile?: File;
  jobText?: string;
}

export async function generateResume({
  reference,
  profile,
  jobDescriptionFile,
  jobText,
}: GenerateResumeParams): Promise<ResumeDocumentPayload> {
  const formData = new FormData();
  formData.append('reference', reference);
  formData.append('profile', profile);

  if (jobDescriptionFile) {
    formData.append('job_description', jobDescriptionFile);
  }

  if (jobText) {
    formData.append('job_text', jobText);
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

export function buildDownloadName(profileName?: string) {
  if (profileName === undefined || profileName.trim() === '') {
    return 'resume.pdf';
  }
  return profileName.replace(/\s+/g, '_').toLowerCase() + '_resume.pdf';
}
