import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Badge,
  Box,
  Button,
  Divider,
  FormControl,
  FormErrorMessage,
  FormHelperText,
  FormLabel,
  Heading,
  Input,
  Stack,
  Text,
  Textarea,
  useBoolean,
  VStack,
} from '@chakra-ui/react';
import { useCallback } from 'react';
import { Controller, useForm } from 'react-hook-form';

import type { GenerateResumeParams } from '@/features/generator/api';

interface GeneratorFormProps {
  onGenerate: (params: GenerateResumeParams) => Promise<void>;
  isGenerating: boolean;
}

interface GeneratorFormValues {
  reference: FileList;
  profile: FileList;
  jobDescriptionFile?: FileList;
  jobText?: string;
}

function fileFromList(list?: FileList | null): File | null {
  if (!list || list.length === 0) {
    return null;
  }
  return list.item(0);
}

export function GeneratorForm({ onGenerate, isGenerating }: GeneratorFormProps) {
  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitSuccessful },
  } = useForm<GeneratorFormValues>({
    defaultValues: {
      jobText: '',
    },
  });
  const [hasSubmitted, setHasSubmitted] = useBoolean();

  const submit = useCallback(
    handleSubmit(async (values) => {
      const reference = fileFromList(values.reference);
      const profile = fileFromList(values.profile);

      if (!reference || !profile) {
        return;
      }

      await onGenerate({
        reference,
        profile,
        jobDescriptionFile: fileFromList(values.jobDescriptionFile ?? null) ?? undefined,
        jobText: values.jobText?.trim() ? values.jobText.trim() : undefined,
      });
      setHasSubmitted.on();
    }),
    [handleSubmit, onGenerate, setHasSubmitted],
  );

  const handleReset = useCallback(() => {
    reset();
    setHasSubmitted.off();
  }, [reset, setHasSubmitted]);

  return (
    <Box
      as="form"
      onSubmit={submit}
      borderWidth="1px"
      borderColor="border.muted"
      borderRadius="2xl"
      bg="surface.card"
      p={{ base: 5, md: 6 }}
      boxShadow="sm"
    >
      <VStack align="flex-start" spacing={6}>
        <VStack align="flex-start" spacing={2}>
          <Badge colorScheme="purple" borderRadius="full" px={3} py={1}>
            Step 1 · Required
          </Badge>
          <Heading fontSize="lg" fontWeight="semibold">
            Upload your baseline files
          </Heading>
          <Text fontSize="sm" color="text.subtle">
            We copy structure from your reference resume and populate it with profile data before tailoring it to the job
            description.
          </Text>
        </VStack>

        <Stack spacing={5} w="full">
          <FormControl isInvalid={Boolean(errors.reference)}>
            <FormLabel fontSize="sm" color="text.subtle">
              Reference Resume (PDF)
            </FormLabel>
            <Input
              type="file"
              accept="application/pdf"
              {...register('reference', {
                validate: (value) => (value && value.length > 0) || 'Reference resume is required.',
              })}
              bg="surface.card"
              borderColor="border.muted"
              _hover={{ borderColor: 'brand.300' }}
            />
            <FormErrorMessage>{errors.reference?.message}</FormErrorMessage>
            <FormHelperText color="text.muted">
              We use your existing resume as structure and styling guidance.
            </FormHelperText>
          </FormControl>

          <FormControl isInvalid={Boolean(errors.profile)}>
            <FormLabel fontSize="sm" color="text.subtle">
              Profile (JSON or YAML)
            </FormLabel>
            <Input
              type="file"
              accept=".json,.yaml,.yml,application/json,text/yaml"
              {...register('profile', {
                validate: (value) => (value && value.length > 0) || 'Profile file is required.',
              })}
              bg="surface.card"
              borderColor="border.muted"
              _hover={{ borderColor: 'brand.300' }}
            />
            <FormErrorMessage>{errors.profile?.message}</FormErrorMessage>
            <FormHelperText color="text.muted">
              Export from Resume-by-JD or upload your saved profile file (JSON or YAML).
            </FormHelperText>
          </FormControl>

          <Divider borderColor="border.muted" />

          <VStack align="flex-start" spacing={2}>
            <Badge colorScheme="purple" borderRadius="full" px={3} py={1} variant="outline">
              Optional · Boost alignment
            </Badge>
            <Text fontSize="sm" color="text.subtle">
              Provide the job description so we can highlight relevant keywords and impact metrics.
            </Text>
          </VStack>

          <FormControl>
            <FormLabel fontSize="sm" color="text.subtle">
              Job Description (PDF or TXT)
            </FormLabel>
            <Controller
              name="jobDescriptionFile"
              control={control}
              render={({ field }) => (
                <Input
                  type="file"
                  accept=".pdf,.txt"
                  ref={field.ref}
                  onChange={(event) => field.onChange(event.target.files ?? null)}
                  bg="surface.card"
                  borderColor="border.muted"
                  _hover={{ borderColor: 'brand.300' }}
                />
              )}
            />
            <FormHelperText color="text.muted">
              Attach the JD document to extract keywords automatically.
            </FormHelperText>
          </FormControl>

          <FormControl>
            <FormLabel fontSize="sm" color="text.subtle">
              Job Description Text
            </FormLabel>
            <Textarea
              minH="120px"
              placeholder="Paste highlights or responsibilities from the job posting…"
              {...register('jobText')}
              bg="surface.card"
              borderColor="border.muted"
              _hover={{ borderColor: 'brand.300' }}
            />
            <FormHelperText color="text.muted">
              Paste snippets if the posting is online only. File upload and text can be combined.
            </FormHelperText>
          </FormControl>
        </Stack>

        <Stack direction={{ base: 'column', sm: 'row' }} spacing={4} w="full">
          <Button type="submit" colorScheme="brand" flex="1" isLoading={isGenerating}>
            Generate Resume
          </Button>
          <Button onClick={handleReset} variant="ghost" colorScheme="gray" flex={{ base: '1', sm: 'initial' }}>
            Clear
          </Button>
        </Stack>

        {hasSubmitted && isSubmitSuccessful && (
          <Alert status="success" variant="left-accent" bg="surface.subtle" borderRadius="lg" borderLeftWidth="6px" borderColor="green.400">
            <AlertIcon color="green.500" />
            <Box>
              <AlertTitle color="green.700">Uploaded!</AlertTitle>
              <AlertDescription color="text.subtle">
                We&apos;ll craft your resume and refresh the preview automatically.
              </AlertDescription>
            </Box>
          </Alert>
        )}
      </VStack>
    </Box>
  );
}
