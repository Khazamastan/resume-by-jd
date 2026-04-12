import {
  Box,
  Button,
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
  Stack,
  SimpleGrid,
  Tag,
  Text,
  Textarea,
  Tooltip,
  useToast,
  VStack,
} from '@chakra-ui/react';
import { useEffect } from 'react';
import {
  type Control,
  Controller,
  useFieldArray,
  useForm,
  type UseFormRegister,
  type UseFormWatch,
} from 'react-hook-form';
import { FiPlus, FiTrash2 } from 'react-icons/fi';

import {
  mapFormToSections,
  mapHeaderToProfile,
  mapProfileToHeader,
  mapSectionsToForm,
  ResumeEditorFormValues,
  SectionKind,
} from '@/features/editor/types/formTypes';
import type { ResumeDocumentPayload, ResumeProfile, ResumeSection } from '@/features/shared/types';
import { usePdfUrl } from '@/features/shared/usePdfUrl';

const PREVIEW_MIN_WIDTH = 840;

interface EditResumeModalProps {
  isOpen: boolean;
  onClose: () => void;
  session: ResumeDocumentPayload | null;
  onUpdated: (args: {
    resumeId: string;
    sections: ResumeSection[];
    profile: ResumeProfile;
    theme?: Record<string, unknown>;
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
    formState: { isDirty },
  } = useForm<ResumeEditorFormValues>({
    defaultValues: {
      header: mapProfileToHeader(session?.profile, session?.sections),
      sections: session ? mapSectionsToForm(session.sections) : [],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'sections',
  });

  useEffect(() => {
    if (!session) {
      reset({
        header: mapProfileToHeader(null, null),
        sections: [],
      });
      return;
    }
    reset({
      header: mapProfileToHeader(session.profile, session.sections),
      sections: mapSectionsToForm(session.sections),
    });
  }, [session, reset]);

  const pdfUrl = usePdfUrl(session?.pdf ?? null);

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
      const updated = await onUpdated({
        resumeId: session.resume_id,
        sections,
        profile,
        theme: session.theme,
      });
      reset({
        header: mapProfileToHeader(updated.profile, updated.sections),
        sections: mapSectionsToForm(updated.sections),
      });
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
                        placeholder="Serving Notice Period – Available to Join: May 5, 2026"
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
          <HStack w="full" justify="flex-end" spacing={2}>
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
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}

type SectionPath = `sections.${number}`;

interface SectionEditorProps {
  control: Control<ResumeEditorFormValues>;
  register: UseFormRegister<ResumeEditorFormValues>;
  watch: UseFormWatch<ResumeEditorFormValues>;
  index: number;
  onRemove: () => void;
}

function SectionEditor({ control, register, watch, index, onRemove }: SectionEditorProps) {
  const path = `sections.${index}` as SectionPath;
  const section = watch(path) as ResumeEditorFormValues['sections'][number] | undefined;
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
