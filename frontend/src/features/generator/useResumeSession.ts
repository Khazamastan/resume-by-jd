import { useMutation } from '@tanstack/react-query';
import { useCallback, useState } from 'react';

import { fetchResume, generateResume, GenerateResumeParams, updateResume } from '@/features/generator/api';
import type { ResumeDocumentPayload, ResumeProfile, ResumeSection } from '@/features/shared/types';

export interface UpdateResumeArgs {
  resumeId: string;
  sections: ResumeSection[];
  profile: ResumeProfile;
  theme?: Record<string, unknown>;
  resumeText?: string;
}

export function useResumeSession() {
  const [session, setSession] = useState<ResumeDocumentPayload | null>(null);

  const generateMutation = useMutation({
    mutationKey: ['generate-resume'],
    mutationFn: (payload: GenerateResumeParams) => generateResume(payload),
    onSuccess: (data) => setSession(data),
  });

  const updateMutation = useMutation({
    mutationKey: ['update-resume'],
    mutationFn: ({ resumeId, sections, profile, theme, resumeText }: UpdateResumeArgs) =>
      updateResume(resumeId, { sections, profile, theme, resumeText }),
    onSuccess: (data) => setSession(data),
  });

  const loadMutation = useMutation({
    mutationKey: ['load-resume-session'],
    mutationFn: (resumeId: string) => fetchResume(resumeId),
    onSuccess: (data) => setSession(data),
  });

  const reset = useCallback(() => {
    setSession(null);
  }, []);

  return {
    session,
    isGenerating: generateMutation.isPending,
    generateError: generateMutation.error,
    updateError: updateMutation.error,
    isUpdating: updateMutation.isPending,
    loadError: loadMutation.error,
    isLoadingSession: loadMutation.isPending,
    generate: generateMutation.mutateAsync,
    update: updateMutation.mutateAsync,
    loadById: loadMutation.mutateAsync,
    reset,
  };
}
