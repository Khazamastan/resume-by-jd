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
  resumeText?: string;
  sampleProfile?: string;
  accentColor?: string;
  primaryColor?: string;
  atsFontFamily?: string;
  bodySize?: number;
  headingSize?: number;
}

export async function generateResume({
  reference,
  profile,
  jobDescriptionFile,
  jobText,
  resumeText,
  sampleProfile,
  accentColor,
  primaryColor,
  atsFontFamily,
  bodySize,
  headingSize,
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

  if (resumeText) {
    formData.append('resume_text', resumeText);
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

  if (atsFontFamily) {
    formData.append('ats_font_family', atsFontFamily);
  }

  if (typeof bodySize === 'number' && Number.isFinite(bodySize)) {
    formData.append('body_size', String(bodySize));
  }

  if (typeof headingSize === 'number' && Number.isFinite(headingSize)) {
    formData.append('heading_size', String(headingSize));
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
  payload: { sections: unknown[]; profile?: ResumeProfile; theme?: Record<string, unknown>; resumeText?: string },
): Promise<ResumeDocumentPayload> {
  const requestPayload = {
    sections: payload.sections,
    profile: payload.profile,
    theme: payload.theme,
    resume_text: payload.resumeText,
  };
  const { data } = await api.put<ResumeDocumentPayload>('/api/resume/' + resumeId, requestPayload);
  return data;
}

export async function fetchResume(resumeId: string): Promise<ResumeDocumentPayload> {
  const { data } = await api.get<ResumeDocumentPayload>('/api/resume/' + resumeId);
  return data;
}

const DEFAULT_DOWNLOAD_NAME = 'Khajamastan-Bellamkonda.pdf';
const DEFAULT_ATS_DOWNLOAD_NAME = 'Khajamastan-Bellamkonda-ATS.pdf';
const DEFAULT_LATEX_DOWNLOAD_NAME = 'Khajamastan-Bellamkonda-LaTeX.pdf';

export function buildDownloadName(_profileName?: string) {
  return DEFAULT_DOWNLOAD_NAME;
}

export function buildAtsDownloadName(_profileName?: string) {
  return DEFAULT_ATS_DOWNLOAD_NAME;
}

export function buildLatexDownloadName(_profileName?: string) {
  return DEFAULT_LATEX_DOWNLOAD_NAME;
}
