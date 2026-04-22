import {
  Box,
  Button,
  ButtonGroup,
  Flex,
  FormControl,
  FormLabel,
  Grid,
  GridItem,
  Heading,
  HStack,
  Icon,
  IconButton,
  Input,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Select,
  Stack,
  SimpleGrid,
  Tag,
  Text,
  Textarea,
  Tooltip,
  useToast,
  VStack,
} from '@chakra-ui/react';
import { useCallback, useEffect, useMemo, useRef } from 'react';
import {
  type Control,
  Controller,
  useFieldArray,
  useForm,
  useWatch,
  type UseFormRegister,
  type UseFormWatch,
} from 'react-hook-form';
import { FiDownload, FiExternalLink, FiPlus, FiTrash2 } from 'react-icons/fi';

import {
  mapFormToSections,
  mapHeaderToProfile,
  mapProfileToHeader,
  mapSectionsToForm,
  ResumeEditorFormValues,
  SectionKind,
} from '@/features/editor/types/formTypes';
import { buildAtsDownloadName, buildDownloadName, buildLatexDownloadName } from '@/features/generator/api';
import type { ResumeDocumentPayload, ResumeProfile, ResumeSection } from '@/features/shared/types';
import { usePdfUrl } from '@/features/shared/usePdfUrl';

const PREVIEW_MIN_WIDTH = 840;
const FALLBACK_ACCENT = '#1a1a1a';
const HEX_COLOR_PATTERN = /^#?(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;
const FALLBACK_ATS_FONT = 'Calibri';
const FALLBACK_BODY_FONT_SIZE = 10;
const FALLBACK_HEADING_FONT_SIZE = 12;
const MIN_FONT_SIZE = 6;
const MAX_FONT_SIZE = 24;
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

type EditResumeFormValues = ResumeEditorFormValues & {
  resumeText: string;
  accentColor: string;
  atsFontFamily: string;
  bodySize: number;
  headingSize: number;
};

function normalizeHexColor(value: string): string | null {
  const candidate = value.trim();
  if (!candidate) {
    return null;
  }
  if (!HEX_COLOR_PATTERN.test(candidate)) {
    return null;
  }
  const withHash = candidate.startsWith('#') ? candidate : `#${candidate}`;
  if (withHash.length === 4) {
    return `#${withHash
      .slice(1)
      .split('')
      .map((token) => `${token}${token}`)
      .join('')
      .toLowerCase()}`;
  }
  return withHash.toLowerCase();
}

function themeAccent(theme?: Record<string, unknown> | null): string {
  const accentRaw = theme?.accent_color;
  if (typeof accentRaw === 'string') {
    const normalized = normalizeHexColor(accentRaw);
    if (normalized) {
      return normalized;
    }
  }
  const primaryRaw = theme?.primary_color;
  if (typeof primaryRaw === 'string') {
    const normalized = normalizeHexColor(primaryRaw);
    if (normalized) {
      return normalized;
    }
  }
  return FALLBACK_ACCENT;
}

function themeAtsFontFamily(theme?: Record<string, unknown> | null): string {
  const raw = theme?.ats_font_family;
  if (typeof raw !== 'string') {
    return FALLBACK_ATS_FONT;
  }
  const normalized = raw.trim().toLowerCase();
  if (normalized === 'space grotesk') {
    return 'SpaceGrotesk';
  }
  const found = ATS_FONT_OPTIONS.find((option) => option.toLowerCase() === normalized);
  return found ?? FALLBACK_ATS_FONT;
}

function themeFontSize(theme: Record<string, unknown> | null | undefined, field: 'body_size' | 'heading_size', fallback: number): number {
  const raw = theme?.[field];
  const parsed = typeof raw === 'number' ? raw : typeof raw === 'string' ? Number(raw) : NaN;
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return parsed >= MIN_FONT_SIZE && parsed <= MAX_FONT_SIZE ? parsed : fallback;
}

function styleSignature(accentColor: string, atsFontFamily: string, bodySize: number, headingSize: number): string {
  const accent = normalizeHexColor(accentColor) ?? accentColor.trim().toLowerCase();
  const font = (atsFontFamily || '').trim().toLowerCase();
  const body = Number.isFinite(bodySize) ? bodySize : FALLBACK_BODY_FONT_SIZE;
  const heading = Number.isFinite(headingSize) ? headingSize : FALLBACK_HEADING_FONT_SIZE;
  return `${accent}|${font}|${body}|${heading}`;
}

interface EditResumeModalProps {
  isOpen: boolean;
  onClose: () => void;
  session: ResumeDocumentPayload | null;
  onUpdated: (args: {
    resumeId: string;
    sections: ResumeSection[];
    profile: ResumeProfile;
    theme?: Record<string, unknown>;
    resumeText?: string;
  }) => Promise<ResumeDocumentPayload>;
  isUpdating: boolean;
}

export function EditResumeModal({ isOpen, onClose, session, onUpdated, isUpdating }: EditResumeModalProps) {
  const toast = useToast();

  const {
    control,
    register,
    handleSubmit,
    reset,
    watch,
    getValues,
    formState: { isDirty },
  } = useForm<EditResumeFormValues>({
    defaultValues: {
      header: mapProfileToHeader(session?.profile, session?.sections),
      sections: session ? mapSectionsToForm(session.sections) : [],
      resumeText: '',
      accentColor: themeAccent(session?.theme),
      atsFontFamily: themeAtsFontFamily(session?.theme),
      bodySize: themeFontSize(session?.theme, 'body_size', FALLBACK_BODY_FONT_SIZE),
      headingSize: themeFontSize(session?.theme, 'heading_size', FALLBACK_HEADING_FONT_SIZE),
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'sections',
  });
  const autoStyleUpdateTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingAutoStyleUpdateRef = useRef(false);
  const initialStyleSignatureRef = useRef<string | null>(null);
  const [watchedAccentColor, watchedAtsFontFamily, watchedBodySize, watchedHeadingSize] = useWatch({
    control,
    name: ['accentColor', 'atsFontFamily', 'bodySize', 'headingSize'],
  });
  const currentStyleSignature = useMemo(
    () =>
      styleSignature(
        watchedAccentColor ?? FALLBACK_ACCENT,
        watchedAtsFontFamily ?? FALLBACK_ATS_FONT,
        Number(watchedBodySize),
        Number(watchedHeadingSize),
      ),
    [watchedAccentColor, watchedAtsFontFamily, watchedBodySize, watchedHeadingSize],
  );

  useEffect(() => {
    if (!session) {
      if (autoStyleUpdateTimeoutRef.current) {
        clearTimeout(autoStyleUpdateTimeoutRef.current);
      }
      pendingAutoStyleUpdateRef.current = false;
      initialStyleSignatureRef.current = styleSignature(
        FALLBACK_ACCENT,
        FALLBACK_ATS_FONT,
        FALLBACK_BODY_FONT_SIZE,
        FALLBACK_HEADING_FONT_SIZE,
      );
      reset({
        header: mapProfileToHeader(null, null),
        sections: [],
        resumeText: '',
        accentColor: FALLBACK_ACCENT,
        atsFontFamily: FALLBACK_ATS_FONT,
        bodySize: FALLBACK_BODY_FONT_SIZE,
        headingSize: FALLBACK_HEADING_FONT_SIZE,
      });
      return;
    }
    if (autoStyleUpdateTimeoutRef.current) {
      clearTimeout(autoStyleUpdateTimeoutRef.current);
    }
    pendingAutoStyleUpdateRef.current = false;
    initialStyleSignatureRef.current = styleSignature(
      themeAccent(session.theme),
      themeAtsFontFamily(session.theme),
      themeFontSize(session.theme, 'body_size', FALLBACK_BODY_FONT_SIZE),
      themeFontSize(session.theme, 'heading_size', FALLBACK_HEADING_FONT_SIZE),
    );
    reset({
      header: mapProfileToHeader(session.profile, session.sections),
      sections: mapSectionsToForm(session.sections),
      resumeText: '',
      accentColor: themeAccent(session.theme),
      atsFontFamily: themeAtsFontFamily(session.theme),
      bodySize: themeFontSize(session.theme, 'body_size', FALLBACK_BODY_FONT_SIZE),
      headingSize: themeFontSize(session.theme, 'heading_size', FALLBACK_HEADING_FONT_SIZE),
    });
  }, [session, reset]);

  const pdfUrl = usePdfUrl(session?.pdf ?? null);
  const atsPdfUrl = usePdfUrl(session?.ats_pdf ?? null);
  const latexPdfUrl = usePdfUrl(session?.latex_pdf ?? null);
  const downloadName = buildDownloadName(session?.profile?.name);
  const atsDownloadName = buildAtsDownloadName(session?.profile?.name);
  const latexDownloadName = buildLatexDownloadName(session?.profile?.name);

  const handleOpenNewTab = () => {
    if (!pdfUrl) {
      return;
    }
    window.open(pdfUrl, '_blank', 'noopener,noreferrer');
  };

  const handleOpenAtsNewTab = () => {
    if (!atsPdfUrl) {
      return;
    }
    window.open(atsPdfUrl, '_blank', 'noopener,noreferrer');
  };

  const handleOpenLatexNewTab = () => {
    if (latexPdfUrl) {
      window.open(latexPdfUrl, '_blank', 'noopener,noreferrer');
      return;
    }
    if (!session?.resume_id) {
      return;
    }
    window.open(`/api/resume/${session.resume_id}/latex-pdf`, '_blank', 'noopener,noreferrer');
  };

  const handleDownload = () => {
    if (!pdfUrl) {
      return;
    }
    const anchor = document.createElement('a');
    anchor.href = pdfUrl;
    anchor.download = downloadName;
    anchor.click();
  };

  const handleDownloadAts = () => {
    if (!atsPdfUrl) {
      return;
    }
    const anchor = document.createElement('a');
    anchor.href = atsPdfUrl;
    anchor.download = atsDownloadName;
    anchor.click();
  };

  const handleDownloadLatex = () => {
    if (!session?.resume_id && !latexPdfUrl) {
      return;
    }
    const anchor = document.createElement('a');
    anchor.href = latexPdfUrl ?? `/api/resume/${session?.resume_id}/latex-pdf`;
    anchor.download = latexDownloadName;
    anchor.click();
  };

  const runAutoStyleUpdate = useCallback(async () => {
    if (!session || !isOpen || !pendingAutoStyleUpdateRef.current || isUpdating) {
      return;
    }
    pendingAutoStyleUpdateRef.current = false;

    const values = getValues();
    const normalizedAccent = normalizeHexColor(values.accentColor);
    const bodySize = Number(values.bodySize);
    const headingSize = Number(values.headingSize);
    if (!normalizedAccent) {
      return;
    }
    if (!Number.isFinite(bodySize) || bodySize < MIN_FONT_SIZE || bodySize > MAX_FONT_SIZE) {
      return;
    }
    if (!Number.isFinite(headingSize) || headingSize < MIN_FONT_SIZE || headingSize > MAX_FONT_SIZE) {
      return;
    }

    const sections = mapFormToSections(values.sections);
    const profile = mapHeaderToProfile(values.header);
    const selectedAtsFont = values.atsFontFamily?.trim() || FALLBACK_ATS_FONT;
    const nextTheme = {
      ...(session.theme ?? {}),
      accent_color: normalizedAccent,
      primary_color: normalizedAccent,
      ats_font_family: selectedAtsFont,
      body_size: bodySize,
      heading_size: headingSize,
    };

    try {
      const updated = await onUpdated({
        resumeId: session.resume_id,
        sections,
        profile,
        theme: nextTheme,
      });
      const nextAccent = themeAccent(updated.theme);
      const nextFont = themeAtsFontFamily(updated.theme);
      const nextBodySize = themeFontSize(updated.theme, 'body_size', FALLBACK_BODY_FONT_SIZE);
      const nextHeadingSize = themeFontSize(updated.theme, 'heading_size', FALLBACK_HEADING_FONT_SIZE);
      initialStyleSignatureRef.current = styleSignature(nextAccent, nextFont, nextBodySize, nextHeadingSize);
      reset({
        header: mapProfileToHeader(updated.profile, updated.sections),
        sections: mapSectionsToForm(updated.sections),
        resumeText: values.resumeText,
        accentColor: nextAccent,
        atsFontFamily: nextFont,
        bodySize: nextBodySize,
        headingSize: nextHeadingSize,
      });
    } catch {
      // Keep modal responsive; updateError toast is surfaced by parent mutation state.
    }
  }, [getValues, isOpen, isUpdating, onUpdated, reset, session]);

  useEffect(() => {
    if (!isOpen || !session) {
      return;
    }
    if (initialStyleSignatureRef.current === null) {
      initialStyleSignatureRef.current = currentStyleSignature;
      return;
    }
    if (currentStyleSignature === initialStyleSignatureRef.current) {
      return;
    }
    pendingAutoStyleUpdateRef.current = true;
    if (autoStyleUpdateTimeoutRef.current) {
      clearTimeout(autoStyleUpdateTimeoutRef.current);
    }
    autoStyleUpdateTimeoutRef.current = setTimeout(() => {
      void runAutoStyleUpdate();
    }, 450);
  }, [currentStyleSignature, isOpen, runAutoStyleUpdate, session]);

  useEffect(() => {
    if (!isOpen || !session) {
      return;
    }
    if (!isUpdating && pendingAutoStyleUpdateRef.current) {
      if (autoStyleUpdateTimeoutRef.current) {
        clearTimeout(autoStyleUpdateTimeoutRef.current);
      }
      autoStyleUpdateTimeoutRef.current = setTimeout(() => {
        void runAutoStyleUpdate();
      }, 120);
    }
  }, [isOpen, isUpdating, runAutoStyleUpdate, session]);

  useEffect(() => {
    return () => {
      if (autoStyleUpdateTimeoutRef.current) {
        clearTimeout(autoStyleUpdateTimeoutRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (isOpen) {
      return;
    }
    if (autoStyleUpdateTimeoutRef.current) {
      clearTimeout(autoStyleUpdateTimeoutRef.current);
    }
    pendingAutoStyleUpdateRef.current = false;
  }, [isOpen]);

  const submit = handleSubmit(async (values) => {
    if (!session) {
      toast({
        title: 'No resume loaded',
        description: 'Generate a resume before editing sections.',
        status: 'warning',
      });
      return;
    }
    try {
      const sections = mapFormToSections(values.sections);
      const profile = mapHeaderToProfile(values.header);
      const resumeText = values.resumeText.trim();
      const normalizedAccent = normalizeHexColor(values.accentColor);
      const selectedAtsFont = values.atsFontFamily?.trim() || FALLBACK_ATS_FONT;
      const bodySize = Number(values.bodySize);
      const headingSize = Number(values.headingSize);
      if (!normalizedAccent) {
        toast({
          title: 'Invalid accent color',
          description: 'Enter a valid hex color like #1a2b3c.',
          status: 'warning',
        });
        return;
      }
      if (!Number.isFinite(bodySize) || bodySize < MIN_FONT_SIZE || bodySize > MAX_FONT_SIZE) {
        toast({
          title: 'Invalid body font size',
          description: `Body font size must be between ${MIN_FONT_SIZE} and ${MAX_FONT_SIZE}.`,
          status: 'warning',
        });
        return;
      }
      if (!Number.isFinite(headingSize) || headingSize < MIN_FONT_SIZE || headingSize > MAX_FONT_SIZE) {
        toast({
          title: 'Invalid heading font size',
          description: `Heading font size must be between ${MIN_FONT_SIZE} and ${MAX_FONT_SIZE}.`,
          status: 'warning',
        });
        return;
      }
      if (autoStyleUpdateTimeoutRef.current) {
        clearTimeout(autoStyleUpdateTimeoutRef.current);
      }
      pendingAutoStyleUpdateRef.current = false;
      const baseTheme = { ...(session.theme ?? {}) };
      const nextTheme = {
        ...baseTheme,
        accent_color: normalizedAccent,
        primary_color: normalizedAccent,
        ats_font_family: selectedAtsFont,
        body_size: bodySize,
        heading_size: headingSize,
      };
      const updated = await onUpdated({
        resumeId: session.resume_id,
        sections,
        profile,
        theme: nextTheme,
        resumeText: resumeText || undefined,
      });
      reset({
        header: mapProfileToHeader(updated.profile, updated.sections),
        sections: mapSectionsToForm(updated.sections),
        resumeText: '',
        accentColor: themeAccent(updated.theme),
        atsFontFamily: themeAtsFontFamily(updated.theme),
        bodySize: themeFontSize(updated.theme, 'body_size', FALLBACK_BODY_FONT_SIZE),
        headingSize: themeFontSize(updated.theme, 'heading_size', FALLBACK_HEADING_FONT_SIZE),
      });
      initialStyleSignatureRef.current = styleSignature(
        themeAccent(updated.theme),
        themeAtsFontFamily(updated.theme),
        themeFontSize(updated.theme, 'body_size', FALLBACK_BODY_FONT_SIZE),
        themeFontSize(updated.theme, 'heading_size', FALLBACK_HEADING_FONT_SIZE),
      );
      toast({
        title: 'Resume updated',
        description: 'Preview refreshed with your latest edits.',
        status: 'success',
      });
    } catch (error) {
      toast({
        title: 'Update failed',
        description: error instanceof Error ? error.message : 'Unable to update resume right now.',
        status: 'error',
      });
    }
  });

  const addSection = () => {
    append({
      title: 'New Section',
      kind: SectionKind.Generic,
      paragraphs: '',
      bullets: '',
      categoryLines: [],
      experiences: [],
      rawMeta: {},
    });
  };

  if (!isOpen) {
    return null;
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="full">
      <ModalOverlay bg="rgba(45,55,72,0.35)" backdropFilter="blur(10px)" />
      <ModalContent bg="surface.canvas" color="text.primary">
        <ModalHeader borderBottomWidth="1px" borderColor="border.muted" bg="surface.card">
          <HStack justify="space-between" align="center">
            <VStack align="flex-start" spacing={1}>
              <Heading fontSize="xl" fontWeight="bold">
                Edit Resume
              </Heading>
              <Text fontSize="xs" color="text.subtle">
                Update header details and sections, then use Save & Refresh.
              </Text>
            </VStack>
            <Tag size="sm" variant="subtle" colorScheme="brand" borderRadius="full" px={3} py={0.5}>
              Live session
            </Tag>
          </HStack>
        </ModalHeader>
        <ModalCloseButton top={3} right={3} />
        <ModalBody p={0}>
          <Grid templateColumns={{ base: '1fr', xl: `minmax(0, 1fr) ${PREVIEW_MIN_WIDTH}px` }} h="calc(100vh - 168px)">
            <GridItem overflowY="auto" px={{ base: 4, md: 6 }} py={5} display="flex" justifyContent="center">
              <Stack spacing={6} as="form" id="resume-editor-form" onSubmit={submit} w="full" maxW="980px">
                <Box borderWidth="1px" borderColor="border.muted" borderRadius="xl" p={{ base: 4, md: 5 }} bg="surface.card" boxShadow="sm">
                  <VStack align="flex-start" spacing={1} mb={4}>
                    <Heading fontSize="lg" color="text.primary">
                      Resume Text, Accent & Font
                    </Heading>
                    <Text fontSize="xs" textTransform="uppercase" letterSpacing="widest" color="text.muted">
                      Paste full resume text to re-parse content, and adjust highlight accent and font.
                    </Text>
                  </VStack>
                  <Stack spacing={4}>
                    <FormControl>
                      <FormLabel fontSize="xs" color="text.subtle">
                        Resume Font Family
                      </FormLabel>
                      <Select
                        {...register('atsFontFamily')}
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
                      <Text fontSize="xs" color="text.muted" mt={1}>
                        Changing font regenerates ATS and Hackajob PDF output on save.
                      </Text>
                    </FormControl>
                    <SimpleGrid columns={{ base: 1, md: 2 }} spacing={3}>
                      <FormControl>
                        <FormLabel fontSize="xs" color="text.subtle">
                          Body Font Size (pt)
                        </FormLabel>
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
                        <FormLabel fontSize="xs" color="text.subtle">
                          Heading Font Size (pt)
                        </FormLabel>
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
                    <Text fontSize="xs" color="text.muted" mt={-1}>
                      Font size range: {MIN_FONT_SIZE} to {MAX_FONT_SIZE} pt.
                    </Text>
                    <FormControl>
                      <FormLabel fontSize="xs" color="text.subtle">
                        Accent Color
                      </FormLabel>
                      <Controller
                        name="accentColor"
                        control={control}
                        render={({ field }) => (
                          <HStack align="center" spacing={3}>
                            <Input
                              type="color"
                              value={normalizeHexColor(field.value) ?? FALLBACK_ACCENT}
                              onChange={field.onChange}
                              p={1}
                              h="42px"
                              w="60px"
                              minW="60px"
                              bg="surface.card"
                              borderColor="border.muted"
                              _hover={{ borderColor: 'brand.300' }}
                            />
                            <Input
                              placeholder="#1a1a1a"
                              value={field.value}
                              onChange={field.onChange}
                              bg="surface.card"
                              borderColor="border.muted"
                              _hover={{ borderColor: 'brand.300' }}
                            />
                          </HStack>
                        )}
                      />
                      <Text fontSize="xs" color="text.muted" mt={1}>
                        Use a hex value. We apply it to both accent and primary PDF colors.
                      </Text>
                    </FormControl>
                    <FormControl>
                      <FormLabel fontSize="xs" color="text.subtle">
                        Resume Text Override
                      </FormLabel>
                      <Textarea
                        minH="220px"
                        placeholder="Paste your full resume text. On save, this replaces current sections using auto-parse, then refreshes preview."
                        {...register('resumeText')}
                        bg="surface.card"
                        borderColor="border.muted"
                        _hover={{ borderColor: 'brand.300' }}
                      />
                      <Text fontSize="xs" color="text.muted" mt={1}>
                        Leave empty to keep editing current structured sections manually.
                      </Text>
                    </FormControl>
                  </Stack>
                </Box>
                <Box borderWidth="1px" borderColor="border.muted" borderRadius="xl" p={{ base: 4, md: 5 }} bg="surface.card" boxShadow="sm">
                  <VStack align="flex-start" spacing={1} mb={4}>
                    <Heading fontSize="lg" color="text.primary">
                      Header Details
                    </Heading>
                    <Text fontSize="xs" textTransform="uppercase" letterSpacing="widest" color="text.muted">
                      Full Name, Role, Company, Contact, Notice Note
                    </Text>
                  </VStack>
                  <SimpleGrid columns={{ base: 1, md: 2 }} spacing={3}>
                    <FormControl>
                      <FormLabel fontSize="xs" color="text.subtle">
                        Full Name
                      </FormLabel>
                      <Input
                        placeholder="Full name"
                        {...register('header.name')}
                        bg="surface.card"
                        borderColor="border.muted"
                        _hover={{ borderColor: 'brand.300' }}
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel fontSize="xs" color="text.subtle">
                        Role
                      </FormLabel>
                      <Input
                        placeholder="Role / Title"
                        {...register('header.headline')}
                        bg="surface.card"
                        borderColor="border.muted"
                        _hover={{ borderColor: 'brand.300' }}
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel fontSize="xs" color="text.subtle">
                        Company Name
                      </FormLabel>
                      <Input
                        placeholder="Company"
                        {...register('header.company')}
                        bg="surface.card"
                        borderColor="border.muted"
                        _hover={{ borderColor: 'brand.300' }}
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel fontSize="xs" color="text.subtle">
                        Mobile Number
                      </FormLabel>
                      <Input
                        placeholder="+91-xxxxxxxxxx"
                        {...register('header.phone')}
                        bg="surface.card"
                        borderColor="border.muted"
                        _hover={{ borderColor: 'brand.300' }}
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel fontSize="xs" color="text.subtle">
                        Email
                      </FormLabel>
                      <Input
                        placeholder="name@email.com"
                        {...register('header.email')}
                        bg="surface.card"
                        borderColor="border.muted"
                        _hover={{ borderColor: 'brand.300' }}
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel fontSize="xs" color="text.subtle">
                        Location
                      </FormLabel>
                      <Input
                        placeholder="City, Country"
                        {...register('header.location')}
                        bg="surface.card"
                        borderColor="border.muted"
                        _hover={{ borderColor: 'brand.300' }}
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel fontSize="xs" color="text.subtle">
                        LinkedIn URL
                      </FormLabel>
                      <Input
                        placeholder="https://www.linkedin.com/in/..."
                        {...register('header.linkedin')}
                        bg="surface.card"
                        borderColor="border.muted"
                        _hover={{ borderColor: 'brand.300' }}
                      />
                    </FormControl>
                    <FormControl gridColumn={{ base: 'auto', md: 'span 2' }}>
                      <FormLabel fontSize="xs" color="text.subtle">
                        Notice Note
                      </FormLabel>
                      <Textarea
                        placeholder="Serving Notice Period – Available to Join: Immediately"
                        {...register('header.noticeNote')}
                        bg="surface.card"
                        borderColor="border.muted"
                        _hover={{ borderColor: 'brand.300' }}
                        minH="96px"
                      />
                    </FormControl>
                  </SimpleGrid>
                </Box>
                <Stack spacing={4}>
                  {fields.map((section, index) => (
                    <SectionEditor
                      key={section.id}
                      control={control}
                      register={register}
                      watch={watch}
                      index={index}
                      onRemove={() => remove(index)}
                    />
                  ))}
                  <Button leftIcon={<Icon as={FiPlus} />} onClick={addSection} alignSelf="flex-start" variant="outline" colorScheme="gray">
                    Add Section
                  </Button>
                </Stack>
              </Stack>
            </GridItem>
            <GridItem display={{ base: 'none', xl: 'flex' }} borderLeftWidth="1px" borderColor="border.muted" flexDir="column" bg="surface.card" minW={`${PREVIEW_MIN_WIDTH}px`}>
              <Flex px={6} py={4} justify="center">
                <Flex w="full" maxW="820px" align="center" justify="space-between">
                  <Heading fontSize="lg" color="text.primary">
                    PDF Preview
                  </Heading>
                  <Text fontSize="xs" color="text.muted">
                    Refresh after saving edits.
                  </Text>
                </Flex>
              </Flex>
              <Flex flex="1" px={6} pb={6} justify="center">
                <Box w="full" maxW="820px" h="full" borderRadius="xl" borderWidth="1px" borderColor="border.muted" overflow="hidden" bg="surface.subtle">
                  {pdfUrl ? (
                    <iframe key={pdfUrl} title="Resume preview" src={pdfUrl} style={{ width: '100%', height: '100%', border: 'none' }} />
                  ) : (
                    <Flex align="center" justify="center" h="full" px={6} textAlign="center" color="text.muted" bg="surface.card">
                      Generate a resume to see it here.
                    </Flex>
                  )}
                </Box>
              </Flex>
            </GridItem>
          </Grid>
        </ModalBody>
        <ModalFooter borderTopWidth="1px" borderColor="border.muted" bg="surface.card">
          <Flex
            w="full"
            justify="space-between"
            align={{ base: 'stretch', md: 'center' }}
            direction={{ base: 'column', md: 'row' }}
            gap={2}
          >
            <ButtonGroup spacing={2} flexWrap="wrap">
              <Button
                variant="outline"
                colorScheme="gray"
                leftIcon={<Icon as={FiExternalLink} />}
                onClick={handleOpenNewTab}
                isDisabled={!pdfUrl}
              >
                Open in new tab
              </Button>
              <Button
                variant="outline"
                colorScheme="gray"
                leftIcon={<Icon as={FiExternalLink} />}
                onClick={handleOpenAtsNewTab}
                isDisabled={!atsPdfUrl}
              >
                Open ATS in new tab
              </Button>
              <Button
                variant="outline"
                colorScheme="gray"
                leftIcon={<Icon as={FiExternalLink} />}
                onClick={handleOpenLatexNewTab}
                isDisabled={!session?.resume_id}
              >
                Open LaTeX in new tab
              </Button>
              <Button
                variant="outline"
                colorScheme="brand"
                leftIcon={<Icon as={FiDownload} />}
                onClick={handleDownload}
                isDisabled={!pdfUrl}
              >
                Download
              </Button>
              <Button
                variant="outline"
                colorScheme="brand"
                leftIcon={<Icon as={FiDownload} />}
                onClick={handleDownloadAts}
                isDisabled={!atsPdfUrl}
              >
                Download ATS
              </Button>
              <Button
                variant="outline"
                colorScheme="brand"
                leftIcon={<Icon as={FiDownload} />}
                onClick={handleDownloadLatex}
                isDisabled={!session?.resume_id}
              >
                Download LaTeX
              </Button>
            </ButtonGroup>

            <HStack justify="flex-end" spacing={2}>
              <Button variant="ghost" colorScheme="gray" onClick={onClose}>
                Cancel
              </Button>
              <Button
                type="submit"
                form="resume-editor-form"
                colorScheme="brand"
                isLoading={isUpdating}
                isDisabled={!isDirty && !isUpdating}
              >
                Save &amp; Refresh
              </Button>
            </HStack>
          </Flex>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}

type SectionPath = `sections.${number}`;

interface SectionEditorProps {
  control: Control<EditResumeFormValues>;
  register: UseFormRegister<EditResumeFormValues>;
  watch: UseFormWatch<EditResumeFormValues>;
  index: number;
  onRemove: () => void;
}

function SectionEditor({ control, register, watch, index, onRemove }: SectionEditorProps) {
  const path = `sections.${index}` as SectionPath;
  const section = watch(path) as EditResumeFormValues['sections'][number] | undefined;
  const kind = section?.kind ?? SectionKind.Generic;
  const sectionTitle = section?.title ?? '';
  const experienceValues = section?.experiences ?? [];

  const {
    fields: categoryFields,
    append: appendCategory,
    remove: removeCategory,
  } = useFieldArray({
    control,
    name: `${path}.categoryLines` as const,
  });

  const {
    fields: experienceFields,
    append: appendExperience,
    remove: removeExperience,
  } = useFieldArray({
    control,
    name: `${path}.experiences` as const,
  });

  return (
    <Box borderWidth="1px" borderColor="border.muted" borderRadius="xl" p={{ base: 4, md: 5 }} bg="surface.card" boxShadow="sm">
      <HStack justify="space-between" align="flex-start" mb={3}>
        <VStack align="flex-start" spacing={0}>
          <Heading fontSize="md" color="text.primary">
            {sectionTitle || 'Untitled Section'}
          </Heading>
          <Text fontSize="xs" textTransform="uppercase" letterSpacing="widest" color="text.muted">
            {kind}
          </Text>
        </VStack>
        <Tooltip label="Remove section">
          <IconButton aria-label="Remove section" icon={<Icon as={FiTrash2} />} size="sm" variant="ghost" colorScheme="red" onClick={onRemove} />
        </Tooltip>
      </HStack>

      <Stack spacing={4}>
        <Input placeholder="Section Title" {...register(`${path}.title` as const)} bg="surface.card" borderColor="border.muted" _hover={{ borderColor: 'brand.300' }} />

        {kind === SectionKind.Summary && (
          <Textarea
            placeholder="Write a compelling, professional summary tailored to the job."
            minH="180px"
            {...register(`${path}.paragraphs` as const)}
            bg="white"
            borderColor="gray.200"
            _hover={{ borderColor: 'brand.300' }}
          />
        )}

        {kind === SectionKind.TechnicalSkills && (
          <Stack spacing={3}>
            <Text fontSize="xs" color="text.subtle">
              List only skills per category, separated by commas.
            </Text>
            {categoryFields.map((field, idx) => (
              <HStack key={field.id} align="flex-start" spacing={3}>
                <Input
                  placeholder="Category (e.g., Front-End)"
                  {...register(`${path}.categoryLines.${idx}.category` as const)}
                  bg="surface.card"
                  borderColor="border.muted"
                  _hover={{ borderColor: 'brand.300' }}
                />
                <Controller
                  control={control}
                  name={`${path}.categoryLines.${idx}.items` as const}
                  render={({ field: controllerField }) => (
                    <Textarea
                      placeholder="Skills (comma separated)"
                      minH="132px"
                      value={controllerField.value}
                      onChange={controllerField.onChange}
                      bg="surface.card"
                      borderColor="border.muted"
                      _hover={{ borderColor: 'brand.300' }}
                    />
                  )}
                />
                <IconButton aria-label="Remove category line" icon={<Icon as={FiTrash2} />} variant="ghost" colorScheme="red" onClick={() => removeCategory(idx)} />
              </HStack>
            ))}
            <Button leftIcon={<Icon as={FiPlus} />} onClick={() => appendCategory({ category: '', items: '' })} variant="outline" colorScheme="gray" alignSelf="flex-start">
              Add Category
            </Button>
          </Stack>
        )}

        {kind === SectionKind.Experience && (
          <Stack spacing={3}>
            <Flex justify="flex-end">
              <Button
                size="xs"
                leftIcon={<Icon as={FiPlus} />}
                variant="outline"
                colorScheme="gray"
                onClick={() =>
                  appendExperience({
                    role: '',
                    company: '',
                    location: '',
                    date_range: '',
                    bullets: '',
                  })
                }
              >
                Add Role
              </Button>
            </Flex>
            {experienceFields.length > 0 ? (
              <Stack spacing={3}>
                {experienceFields.map((field, idx) => {
                  const role = experienceValues[idx]?.role?.trim() || 'Untitled Role';
                  const company = experienceValues[idx]?.company?.trim() || 'Unknown Company';

                  return (
                    <Box key={field.id} borderWidth="1px" borderColor="border.muted" borderRadius="md" p={2.5} bg="surface.card">
                      <Stack spacing={2}>
                        <HStack justify="space-between" align="center">
                          <Heading fontSize="xs" fontWeight="semibold" color="text.primary">
                            {`${role}-${company}`}
                          </Heading>
                          <IconButton
                            aria-label="Remove role"
                            icon={<Icon as={FiTrash2} />}
                            size="xs"
                            variant="ghost"
                            colorScheme="red"
                            onClick={() => removeExperience(idx)}
                          />
                        </HStack>
                        <SimpleGrid columns={{ base: 1, md: 2, xl: 4 }} spacing={2}>
                          <Input
                            size="sm"
                            placeholder="Role"
                            {...register(`${path}.experiences.${idx}.role` as const)}
                            bg="surface.card"
                            borderColor="border.muted"
                            _hover={{ borderColor: 'brand.300' }}
                          />
                          <Input
                            size="sm"
                            placeholder="Company"
                            {...register(`${path}.experiences.${idx}.company` as const)}
                            bg="surface.card"
                            borderColor="border.muted"
                            _hover={{ borderColor: 'brand.300' }}
                          />
                          <Input
                            size="sm"
                            placeholder="Location"
                            {...register(`${path}.experiences.${idx}.location` as const)}
                            bg="surface.card"
                            borderColor="border.muted"
                            _hover={{ borderColor: 'brand.300' }}
                          />
                          <Input
                            size="sm"
                            placeholder="Date Range"
                            {...register(`${path}.experiences.${idx}.date_range` as const)}
                            bg="surface.card"
                            borderColor="border.muted"
                            _hover={{ borderColor: 'brand.300' }}
                          />
                        </SimpleGrid>
                        <Textarea
                          size="sm"
                          placeholder="Bullets (one per line)"
                          minH="300px"
                          resize="vertical"
                          {...register(`${path}.experiences.${idx}.bullets` as const)}
                          bg="surface.card"
                          borderColor="border.muted"
                          _hover={{ borderColor: 'brand.300' }}
                        />
                      </Stack>
                    </Box>
                  );
                })}
              </Stack>
            ) : (
              <Box>
                <Text fontSize="sm" color="text.muted">
                  Start by adding your first role.
                </Text>
              </Box>
            )}
          </Stack>
        )}

        {kind === SectionKind.Generic && (
          <Stack spacing={3}>
            <Textarea
              placeholder="Paragraphs (separate with blank lines)"
              minH="132px"
              {...register(`${path}.paragraphs` as const)}
              bg="surface.card"
              borderColor="border.muted"
              _hover={{ borderColor: 'brand.300' }}
            />
            <Textarea
              placeholder="Bullets (one per line)"
              minH="132px"
              {...register(`${path}.bullets` as const)}
              bg="surface.card"
              borderColor="border.muted"
              _hover={{ borderColor: 'brand.300' }}
            />
          </Stack>
        )}

        {kind !== SectionKind.Summary && kind !== SectionKind.TechnicalSkills && kind !== SectionKind.Experience && kind !== SectionKind.Generic && (
          <Stack spacing={3}>
            <Textarea
              placeholder="Paragraphs (separate with blank lines)"
              minH="132px"
              {...register(`${path}.paragraphs` as const)}
              bg="surface.card"
              borderColor="border.muted"
              _hover={{ borderColor: 'brand.300' }}
            />
            <Textarea
              placeholder="Bullets (one per line)"
              minH="132px"
              {...register(`${path}.bullets` as const)}
              bg="surface.card"
              borderColor="border.muted"
              _hover={{ borderColor: 'brand.300' }}
            />
          </Stack>
        )}
      </Stack>
    </Box>
  );
}
