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
  Select,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  useBoolean,
  VStack,
} from '@chakra-ui/react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Controller, useForm, useWatch } from 'react-hook-form';

import {
  defaultSampleProfileId,
  fetchSampleProfiles,
  type GenerateResumeParams,
  type SampleProfileSummary,
} from '@/features/generator/api';
import { accentOptions, defaultAccent, getAccentHex, type AccentKey } from '@/theme';
import { useThemeSettings } from '@/theme/ThemeSettingsProvider';

interface GeneratorFormProps {
  onGenerate: (params: GenerateResumeParams) => Promise<void>;
  onAutoGenerate?: (params: GenerateResumeParams) => Promise<void>;
  isGenerating: boolean;
  formId?: string;
}

interface GeneratorFormValues {
  sampleProfile: string;
  reference?: FileList;
  profile?: FileList;
  jobDescriptionFile?: FileList;
  jobText?: string;
  resumeText?: string;
  accentKey: AccentKey;
  atsFontFamily: string;
  bodySize: number;
  headingSize: number;
}

const ATS_FONT_OPTIONS = [
  'Calibri',
  'Arial',
  'Georgia',
  'Helvetica',
  'SpaceGrotesk',
  'Garamond',
  'Tahoma',
  'Times New Roman',
  'Cambria',
  'Montserrat',
  'Lato',
  'Aptos',
];
const DEFAULT_BODY_FONT_SIZE = 10;
const DEFAULT_HEADING_FONT_SIZE = 12;
const MIN_FONT_SIZE = 6;
const MAX_FONT_SIZE = 24;

function fileFromList(list?: FileList | null): File | undefined {
  if (!list || list.length === 0) {
    return undefined;
  }
  return list[0] ?? undefined;
}

function styleSignature(accentKey: AccentKey, atsFontFamily: string, bodySize: number, headingSize: number): string {
  const font = (atsFontFamily || '').trim().toLowerCase();
  const body = Number.isFinite(bodySize) ? bodySize : DEFAULT_BODY_FONT_SIZE;
  const heading = Number.isFinite(headingSize) ? headingSize : DEFAULT_HEADING_FONT_SIZE;
  return `${accentKey}|${font}|${body}|${heading}`;
}

export function GeneratorForm({
  onGenerate,
  onAutoGenerate,
  isGenerating,
  formId = 'generator-form',
}: GeneratorFormProps) {
  const { setAccent } = useThemeSettings();
  const [sampleProfiles, setSampleProfiles] = useState<SampleProfileSummary[]>([]);
  const [sampleProfilesError, setSampleProfilesError] = useState<string | null>(null);
  const [isSampleProfilesLoading, setIsSampleProfilesLoading] = useState(true);
  const autoGenerateTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingAutoGenerateRef = useRef(false);
  const initialStyleSignatureRef = useRef<string | null>(null);

  const {
    control,
    register,
    handleSubmit,
    reset,
    setValue,
    getValues,
    formState: { errors, isSubmitSuccessful },
  } = useForm<GeneratorFormValues>({
    defaultValues: {
      sampleProfile: defaultSampleProfileId,
      jobText: '',
      resumeText: '',
      accentKey: defaultAccent,
      atsFontFamily: 'Calibri',
      bodySize: DEFAULT_BODY_FONT_SIZE,
      headingSize: DEFAULT_HEADING_FONT_SIZE,
    },
  });
  const [hasSubmitted, setHasSubmitted] = useBoolean();
  const [watchedAccentKey, watchedAtsFontFamily, watchedBodySize, watchedHeadingSize] = useWatch({
    control,
    name: ['accentKey', 'atsFontFamily', 'bodySize', 'headingSize'],
  });

  const currentStyleSignature = useMemo(
    () =>
      styleSignature(
        watchedAccentKey ?? defaultAccent,
        watchedAtsFontFamily ?? 'Calibri',
        Number(watchedBodySize),
        Number(watchedHeadingSize),
      ),
    [watchedAccentKey, watchedAtsFontFamily, watchedBodySize, watchedHeadingSize],
  );

  const buildGenerateParams = useCallback(
    (values: GeneratorFormValues): GenerateResumeParams => {
      const reference = fileFromList(values.reference);
      const profile = fileFromList(values.profile);
      const selectedAccent = values.accentKey ?? defaultAccent;
      const accentColor = selectedAccent === 'reference' ? undefined : getAccentHex(selectedAccent);

      return {
        reference: reference ?? undefined,
        profile: profile ?? undefined,
        jobDescriptionFile: fileFromList(values.jobDescriptionFile ?? null) ?? undefined,
        jobText: values.jobText?.trim() ? values.jobText.trim() : undefined,
        resumeText: values.resumeText?.trim() ? values.resumeText.trim() : undefined,
        sampleProfile: values.sampleProfile?.trim() || defaultSampleProfileId,
        accentColor,
        atsFontFamily: values.atsFontFamily?.trim() || 'Calibri',
        bodySize: Number.isFinite(values.bodySize) ? values.bodySize : DEFAULT_BODY_FONT_SIZE,
        headingSize: Number.isFinite(values.headingSize) ? values.headingSize : DEFAULT_HEADING_FONT_SIZE,
      };
    },
    [],
  );

  const autoGenerateHandler = onAutoGenerate ?? onGenerate;

  const runAutoGenerate = useCallback(async () => {
    if (!pendingAutoGenerateRef.current || isGenerating) {
      return;
    }
    pendingAutoGenerateRef.current = false;
    const values = getValues();
    await autoGenerateHandler(buildGenerateParams(values));
    initialStyleSignatureRef.current = styleSignature(
      values.accentKey ?? defaultAccent,
      values.atsFontFamily ?? 'Calibri',
      Number(values.bodySize),
      Number(values.headingSize),
    );
    setHasSubmitted.on();
  }, [autoGenerateHandler, buildGenerateParams, getValues, isGenerating, setHasSubmitted]);

  useEffect(() => {
    let isMounted = true;
    setIsSampleProfilesLoading(true);

    fetchSampleProfiles()
      .then((response) => {
        if (!isMounted) {
          return;
        }
        const nextProfiles = response.profiles ?? [];
        setSampleProfiles(nextProfiles);
        setSampleProfilesError(null);

        const chosenDefault =
          nextProfiles.find((option) => option.id.toLowerCase() === response.default_profile.toLowerCase())?.id ??
          nextProfiles.find((option) => option.id.toLowerCase() === defaultSampleProfileId.toLowerCase())?.id ??
          nextProfiles[0]?.id ??
          defaultSampleProfileId;

        setValue('sampleProfile', chosenDefault, { shouldDirty: false });
      })
      .catch((error) => {
        if (!isMounted) {
          return;
        }
        setSampleProfilesError(error instanceof Error ? error.message : 'Unable to load sample profiles.');
      })
      .finally(() => {
        if (isMounted) {
          setIsSampleProfilesLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [setValue]);

  useEffect(() => {
    if (initialStyleSignatureRef.current === null) {
      initialStyleSignatureRef.current = currentStyleSignature;
      return;
    }
    if (currentStyleSignature === initialStyleSignatureRef.current) {
      return;
    }
    pendingAutoGenerateRef.current = true;
    if (autoGenerateTimeoutRef.current) {
      clearTimeout(autoGenerateTimeoutRef.current);
    }
    autoGenerateTimeoutRef.current = setTimeout(() => {
      void runAutoGenerate();
    }, 450);
  }, [currentStyleSignature, runAutoGenerate]);

  useEffect(() => {
    if (!isGenerating && pendingAutoGenerateRef.current) {
      if (autoGenerateTimeoutRef.current) {
        clearTimeout(autoGenerateTimeoutRef.current);
      }
      autoGenerateTimeoutRef.current = setTimeout(() => {
        void runAutoGenerate();
      }, 120);
    }
  }, [isGenerating, runAutoGenerate]);

  useEffect(() => {
    return () => {
      if (autoGenerateTimeoutRef.current) {
        clearTimeout(autoGenerateTimeoutRef.current);
      }
    };
  }, []);

  const submit = handleSubmit(async (values) => {
    await onGenerate(buildGenerateParams(values));
    initialStyleSignatureRef.current = styleSignature(
      values.accentKey ?? defaultAccent,
      values.atsFontFamily ?? 'Calibri',
      Number(values.bodySize),
      Number(values.headingSize),
    );
    pendingAutoGenerateRef.current = false;
    setHasSubmitted.on();
  });

  const handleReset = useCallback(() => {
    if (autoGenerateTimeoutRef.current) {
      clearTimeout(autoGenerateTimeoutRef.current);
    }
    pendingAutoGenerateRef.current = false;
    initialStyleSignatureRef.current = styleSignature(
      defaultAccent,
      'Calibri',
      DEFAULT_BODY_FONT_SIZE,
      DEFAULT_HEADING_FONT_SIZE,
    );
    reset();
    setHasSubmitted.off();
  }, [reset, setHasSubmitted]);

  const selectableSampleProfiles =
    sampleProfiles.length > 0
      ? sampleProfiles
      : [{ id: defaultSampleProfileId, label: defaultSampleProfileId }];

  return (
    <Box
      as="form"
      id={formId}
      onSubmit={submit}
      w="full"
      maxW={{ base: '100%', xl: '400px' }}
      alignSelf="center"
      borderWidth="1px"
      borderColor="border.muted"
      borderRadius="xl"
      bg="surface.card"
      p={{ base: 4, md: 5 }}
      boxShadow="sm"
    >
      <VStack align="flex-start" spacing={4}>
        <VStack align="flex-start" spacing={1}>
          <Badge colorScheme="brand" borderRadius="full" px={3} py={1}>
            Step 1 · Optional
          </Badge>
          <Heading fontSize="md" fontWeight="semibold">
            Upload baseline files (optional)
          </Heading>
          <Text fontSize="xs" color="text.subtle">
            If omitted, we auto-use `resume.pdf` and `profile.yaml` from your selected sample profile.
          </Text>
        </VStack>

        <Stack spacing={4} w="full">
          <FormControl>
            <FormLabel color="text.subtle">
              Sample Profile
            </FormLabel>
            <Select
              {...register('sampleProfile')}
              bg="surface.card"
              borderColor="border.muted"
              _hover={{ borderColor: 'brand.300' }}
            >
              {selectableSampleProfiles.map((sampleProfileOption) => (
                <option key={sampleProfileOption.id} value={sampleProfileOption.id}>
                  {sampleProfileOption.label}
                </option>
              ))}
            </Select>
            <FormHelperText color="text.muted">
              {sampleProfilesError
                ? `Using default sample (${defaultSampleProfileId}) because profiles could not be loaded.`
                : 'If files are not uploaded, we use this sample folder from `/samples`.'}
            </FormHelperText>
          </FormControl>

          <FormControl isInvalid={Boolean(errors.reference)}>
            <FormLabel color="text.subtle">
              Reference Resume (PDF)
            </FormLabel>
            <Input
              type="file"
              accept="application/pdf"
              {...register('reference')}
              bg="surface.card"
              borderColor="border.muted"
              _hover={{ borderColor: 'brand.300' }}
            />
            <FormErrorMessage>{errors.reference?.message}</FormErrorMessage>
            <FormHelperText color="text.muted">
              Optional. If not uploaded, defaults to `samples/sample-profile/resume.pdf`.
            </FormHelperText>
          </FormControl>

          <FormControl>
            <FormLabel color="text.subtle">
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
              Optional. If not uploaded, defaults to `samples/sample-profile/profile.yaml`.
            </FormHelperText>
          </FormControl>

          <Divider borderColor="border.muted" />

          <VStack align="flex-start" spacing={2}>
            <Badge colorScheme="brand" borderRadius="full" px={3} py={1} variant="outline">
              Optional · Job context
            </Badge>
            <Text fontSize="xs" color="text.subtle">
              If omitted, job description defaults to `N/A`.
            </Text>
          </VStack>

          <FormControl>
            <FormLabel color="text.subtle">
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
            <FormLabel color="text.subtle">
              Job Description Text
            </FormLabel>
            <Textarea
              minH="96px"
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

          <FormControl>
            <FormLabel color="text.subtle">
              Resume Text
            </FormLabel>
            <Textarea
              minH="260px"
              placeholder="Paste your full resume text here. We will parse it into sections, generate the PDF, and load it for editing."
              {...register('resumeText')}
              bg="surface.card"
              borderColor="border.muted"
              _hover={{ borderColor: 'brand.300' }}
            />
            <FormHelperText color="text.muted">
              If provided, this text becomes the source resume content and is auto-filled into the editor.
            </FormHelperText>
          </FormControl>
        </Stack>

        <FormControl>
          <FormLabel color="text.subtle">
            Accent
          </FormLabel>
          <Controller
            name="accentKey"
            control={control}
            render={({ field }) => (
              <SimpleGrid columns={{ base: 2, sm: 3 }} spacing={2} w="full">
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
                      px={2}
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

        <FormControl>
          <FormLabel color="text.subtle">
            Resume Font Family
          </FormLabel>
          <Controller
            name="atsFontFamily"
            control={control}
            render={({ field }) => (
              <Select
                value={field.value}
                onChange={(event) => field.onChange(event.target.value)}
                bg="surface.card"
                borderColor="border.muted"
                _hover={{ borderColor: 'brand.300' }}
              >
                {ATS_FONT_OPTIONS.map((fontOption) => (
                  <option key={fontOption} value={fontOption}>
                    {fontOption}
                  </option>
                ))}
              </Select>
            )}
          />
          <FormHelperText color="text.muted">
            Applies to both ATS and Hackajob resume PDF rendering.
          </FormHelperText>
        </FormControl>

        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={3} w="full">
          <FormControl>
            <FormLabel color="text.subtle">Body Font Size (pt)</FormLabel>
            <Input
              type="number"
              step="0.5"
              min={MIN_FONT_SIZE}
              max={MAX_FONT_SIZE}
              {...register('bodySize', { valueAsNumber: true })}
              bg="surface.card"
              borderColor="border.muted"
              _hover={{ borderColor: 'brand.300' }}
            />
          </FormControl>
          <FormControl>
            <FormLabel color="text.subtle">Heading Font Size (pt)</FormLabel>
            <Input
              type="number"
              step="0.5"
              min={MIN_FONT_SIZE}
              max={MAX_FONT_SIZE}
              {...register('headingSize', { valueAsNumber: true })}
              bg="surface.card"
              borderColor="border.muted"
              _hover={{ borderColor: 'brand.300' }}
            />
          </FormControl>
        </SimpleGrid>
        <Text fontSize="sm" color="text.muted">
          Controls resume text sizes in generated PDF output. Range: {MIN_FONT_SIZE} to {MAX_FONT_SIZE} pt.
        </Text>

        <Button size="sm" onClick={handleReset} variant="ghost" colorScheme="gray" alignSelf="flex-start" isDisabled={isGenerating}>
          Clear
        </Button>

        {hasSubmitted && isSubmitSuccessful && (
          <Alert status="success" variant="left-accent" bg="surface.subtle" borderRadius="lg" borderLeftWidth="6px" borderColor="brand.400">
            <AlertIcon color="brand.500" />
            <Box>
              <AlertTitle color="brand.700">Uploaded!</AlertTitle>
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
