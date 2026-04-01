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
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  useBoolean,
  VStack,
} from '@chakra-ui/react';
import { useCallback } from 'react';
import { Controller, useForm } from 'react-hook-form';

import type { GenerateResumeParams } from '@/features/generator/api';
import { accentOptions, defaultAccent, getAccentHex, type AccentKey } from '@/theme';
import { useThemeSettings } from '@/theme/ThemeSettingsProvider';

interface GeneratorFormProps {
  onGenerate: (params: GenerateResumeParams) => Promise<void>;
  isGenerating: boolean;
}

interface GeneratorFormValues {
  reference: FileList;
  profile?: FileList;
  jobDescriptionFile?: FileList;
  jobText?: string;
  accentKey: AccentKey;
}

function fileFromList(list?: FileList | null): File | null {
  if (!list || list.length === 0) {
    return null;
  }
  return list.item(0);
}

export function GeneratorForm({ onGenerate, isGenerating }: GeneratorFormProps) {
  const { accent: currentAccent, setAccent } = useThemeSettings();
  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitSuccessful },
  } = useForm<GeneratorFormValues>({
    defaultValues: {
      jobText: '',
      accentKey: currentAccent ?? defaultAccent,
    },
  });
  const [hasSubmitted, setHasSubmitted] = useBoolean();

  const submit = handleSubmit(async (values) => {
    const reference = fileFromList(values.reference);
    const profile = fileFromList(values.profile);

    if (!reference) {
      return;
    }

    const selectedAccent = values.accentKey ?? defaultAccent;
    const accentColor = getAccentHex(selectedAccent);

    await onGenerate({
      reference,
      profile: profile ?? undefined,
      jobDescriptionFile: fileFromList(values.jobDescriptionFile ?? null) ?? undefined,
      jobText: values.jobText?.trim() ? values.jobText.trim() : undefined,
      accentColor,
    });
    setHasSubmitted.on();
  });

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
            We copy structure from your reference resume and, if provided, merge in your saved profile before tailoring it
            to the job description.
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

          <FormControl>
            <FormLabel fontSize="sm" color="text.subtle">
              Profile (JSON or YAML)
            </FormLabel>
            <Input
              type="file"
              accept=".json,.yaml,.yml,application/json,text/yaml"
              {...register('profile')}
              bg="surface.card"
              borderColor="border.muted"
              _hover={{ borderColor: 'brand.300' }}
            />
            <FormHelperText color="text.muted">
              Optional. Upload a saved profile file to override the inferred details we derive from your reference resume.
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

        <FormControl>
          <FormLabel fontSize="sm" color="text.subtle">
            Accent
          </FormLabel>
          <Controller
            name="accentKey"
            control={control}
            render={({ field }) => (
              <SimpleGrid columns={{ base: 2, sm: 3 }} spacing={3} w="full">
                {accentOptions.map((option) => {
                  const isSelected = field.value === option.key;
                  const hex = option.swatch;
                  const contrast =
                    (() => {
                      const normalized = hex.replace('#', '');
                      const r = parseInt(normalized.slice(0, 2), 16);
                      const g = parseInt(normalized.slice(2, 4), 16);
                      const b = parseInt(normalized.slice(4, 6), 16);
                      const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
                      return luminance > 0.6 ? 'gray.900' : 'white';
                    })();
                  return (
                    <Button
                      key={option.key}
                      type="button"
                      onClick={() => {
                        field.onChange(option.key);
                        setAccent(option.key);
                      }}
                      bg={option.swatch}
                      color={contrast}
                      variant={isSelected ? 'solid' : 'outline'}
                      borderColor={isSelected ? option.swatch : 'border.muted'}
                      _hover={{ opacity: 0.9 }}
                      boxShadow={isSelected ? 'outline' : undefined}
                      justifyContent="flex-start"
                      px={3}
                    >
                      {option.label}
                    </Button>
                  );
                })}
              </SimpleGrid>
            )}
          />
          <FormHelperText color="text.muted">
            Pick the highlight color that will be applied to the generated resume.
          </FormHelperText>
        </FormControl>

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
