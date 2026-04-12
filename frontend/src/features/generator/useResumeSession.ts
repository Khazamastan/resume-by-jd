import { useMutation } from '@tanstack/react-query';
import { useCallback, useState } from 'react';

import { generateResume, GenerateResumeParams, updateResume } from '@/features/generator/api';
import type { ResumeDocumentPayload, ResumeProfile, ResumeSection } from '@/features/shared/types';

export interface UpdateResumeArgs {
  resumeId: string;
  sections: ResumeSection[];
  profile: ResumeProfile;
  theme?: Record<string, unknown>;
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
    mutationFn: ({ resumeId, sections, profile, theme }: UpdateResumeArgs) => updateResume(resumeId, { sections, profile, theme }),
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
    generate: generateMutation.mutateAsync,
    update: updateMutation.mutateAsync,
    reset,
  };
}
