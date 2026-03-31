import {
  Box,
  Button,
  Divider,
  Flex,
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
  Tab,
  TabList,
  TabPanel,
  TabPanels,
  Tabs,
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

import { mapFormToSections, mapSectionsToForm, ResumeEditorFormValues, SectionKind } from '@/features/editor/types/formTypes';
import type { ResumeDocumentPayload, ResumeSection } from '@/features/shared/types';
import { usePdfUrl } from '@/features/shared/usePdfUrl';

const PREVIEW_MIN_WIDTH = 840;

interface EditResumeModalProps {
  isOpen: boolean;
  onClose: () => void;
  session: ResumeDocumentPayload | null;
  onUpdated: (args: { resumeId: string; sections: ResumeSection[] }) => Promise<ResumeDocumentPayload>;
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
      sections: session ? mapSectionsToForm(session.sections) : [],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'sections',
  });

  useEffect(() => {
    if (!session) {
      reset({ sections: [] });
      return;
    }
    reset({ sections: mapSectionsToForm(session.sections) });
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
      await onUpdated({ resumeId: session.resume_id, sections });
      toast({
        title: 'Resume updated',
        description: 'Preview refreshed with your latest edits.',
        status: 'success',
      });
      onClose();
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
              <Heading fontSize="2xl" fontWeight="extrabold">
                Edit Resume Sections
              </Heading>
              <Text fontSize="sm" color="text.subtle">
                Adjust summary, skills, and experience details. Save to refresh the PDF preview.
              </Text>
            </VStack>
            <Tag variant="subtle" colorScheme="brand" borderRadius="full" px={4} py={1}>
              Live session
            </Tag>
          </HStack>
        </ModalHeader>
        <ModalCloseButton top={4} right={4} />
        <ModalBody p={0}>
          <Grid templateColumns={{ base: '1fr', xl: `minmax(0, 1fr) ${PREVIEW_MIN_WIDTH}px` }} h="calc(100vh - 168px)">
            <GridItem overflowY="auto" px={{ base: 6, md: 10 }} py={8}>
              <Stack spacing={8} as="form" onSubmit={submit}>
                <Stack spacing={6}>
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
                <Divider borderColor="border.muted" />
                <HStack justify="flex-end" spacing={4}>
                  <Button variant="ghost" colorScheme="gray" onClick={onClose}>
                    Cancel
                  </Button>
                  <Button type="submit" colorScheme="brand" isLoading={isUpdating} isDisabled={!isDirty && !isUpdating}>
                    Save &amp; Refresh
                  </Button>
                </HStack>
              </Stack>
            </GridItem>
            <GridItem display={{ base: 'none', xl: 'flex' }} borderLeftWidth="1px" borderColor="border.muted" flexDir="column" bg="surface.card" minW={`${PREVIEW_MIN_WIDTH}px`}>
              <Flex px={10} py={7} align="center" justify="space-between">
                <Heading fontSize="lg" color="text.primary">
                  PDF Preview
                </Heading>
                <Text fontSize="sm" color="text.muted">
                  Refresh after saving edits.
                </Text>
              </Flex>
              <Flex flex="1" px={8} pb={10}>
                <Box w="full" h="full" borderRadius="2xl" borderWidth="1px" borderColor="border.muted" overflow="hidden" bg="surface.subtle">
                  {pdfUrl ? (
                    <iframe title="Resume preview" src={pdfUrl} style={{ width: '100%', height: '100%', border: 'none' }} />
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
        <ModalFooter display={{ base: 'flex', xl: 'none' }} borderTopWidth="1px" borderColor="border.muted" bg="surface.card">
          <HStack w="full" justify="flex-end" spacing={4}>
            <Button variant="ghost" colorScheme="gray" onClick={onClose}>
              Cancel
            </Button>
            <Button onClick={submit} colorScheme="brand" isLoading={isUpdating} isDisabled={!isDirty && !isUpdating}>
              Save &amp; Refresh
            </Button>
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}

interface SectionEditorProps {
  control: Control<ResumeEditorFormValues>;
  register: UseFormRegister<ResumeEditorFormValues>;
  watch: UseFormWatch<ResumeEditorFormValues>;
  index: number;
  onRemove: () => void;
}

function SectionEditor({ control, register, watch, index, onRemove }: SectionEditorProps) {
  const path = `sections.${index}`;
  const kind = watch(`${path}.kind`);

  const {
    fields: categoryFields,
    append: appendCategory,
    remove: removeCategory,
  } = useFieldArray({
    control,
    name: `${path}.categoryLines`,
  });

  const {
    fields: experienceFields,
    append: appendExperience,
    remove: removeExperience,
  } = useFieldArray({
    control,
    name: `${path}.experiences`,
  });

  return (
    <Box borderWidth="1px" borderColor="border.muted" borderRadius="2xl" p={{ base: 5, md: 6 }} bg="surface.card" boxShadow="sm">
      <HStack justify="space-between" align="flex-start" mb={4}>
        <VStack align="flex-start" spacing={0}>
          <Heading fontSize="lg" color="text.primary">
            {watch(`${path}.title`) || 'Untitled Section'}
          </Heading>
          <Text fontSize="xs" textTransform="uppercase" letterSpacing="widest" color="text.muted">
            {kind}
          </Text>
        </VStack>
        <Tooltip label="Remove section">
          <IconButton aria-label="Remove section" icon={<Icon as={FiTrash2} />} size="sm" variant="ghost" colorScheme="red" onClick={onRemove} />
        </Tooltip>
      </HStack>

      <Stack spacing={5}>
        <Input placeholder="Section Title" {...register(`${path}.title` as const)} bg="surface.card" borderColor="border.muted" _hover={{ borderColor: 'brand.300' }} />

        {kind === SectionKind.Summary && (
          <Textarea
            placeholder="Write a compelling, professional summary tailored to the job."
            minH="160px"
            {...register(`${path}.paragraphs` as const)}
            bg="white"
            borderColor="gray.200"
            _hover={{ borderColor: 'brand.300' }}
          />
        )}

        {kind === SectionKind.TechnicalSkills && (
          <Stack spacing={4}>
            <Text fontSize="sm" color="text.subtle">
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
                  name={`${path}.categoryLines.${idx}.items`}
                  render={({ field: controllerField }) => (
                    <Textarea
                      placeholder="Skills (comma separated)"
                      minH="120px"
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
          <Stack spacing={6}>
            <Text fontSize="sm" color="text.subtle">
              Provide details for each role. Bullets support Shift+Enter for multi-line editing.
            </Text>
            <Tabs variant="soft-rounded" colorScheme="brand" isLazy>
              <Flex justify="space-between" align={{ base: 'stretch', md: 'center' }} gap={3} flexWrap="wrap">
                <TabList overflowX="auto" flex="1" bg="surface.subtle" borderRadius="full" px={2} py={1}>
                  {experienceFields.length > 0 ? (
                    experienceFields.map((field, idx) => (
                      <Tab key={field.id} whiteSpace="nowrap">
                        {watch(`${path}.experiences.${idx}.role`) || `Experience ${idx + 1}`}
                      </Tab>
                    ))
                  ) : (
                    <Tab isDisabled>No roles yet</Tab>
                  )}
                </TabList>
                <Button
                  size="sm"
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
                <TabPanels>
                  {experienceFields.map((field, idx) => (
                    <TabPanel key={field.id} px={0} pt={4}>
                      <Stack spacing={4}>
                        <Input
                          placeholder="Role"
                          {...register(`${path}.experiences.${idx}.role` as const)}
                          bg="surface.card"
                          borderColor="border.muted"
                          _hover={{ borderColor: 'brand.300' }}
                        />
                        <Input
                          placeholder="Company"
                          {...register(`${path}.experiences.${idx}.company` as const)}
                          bg="surface.card"
                          borderColor="border.muted"
                          _hover={{ borderColor: 'brand.300' }}
                        />
                        <HStack spacing={3}>
                          <Input
                            placeholder="Location"
                            {...register(`${path}.experiences.${idx}.location` as const)}
                            bg="surface.card"
                            borderColor="border.muted"
                            _hover={{ borderColor: 'brand.300' }}
                          />
                          <Input
                            placeholder="Date Range"
                            {...register(`${path}.experiences.${idx}.date_range` as const)}
                            bg="surface.card"
                            borderColor="border.muted"
                            _hover={{ borderColor: 'brand.300' }}
                          />
                        </HStack>
                        <Textarea
                          placeholder="Bullets (one per line)"
                          minH="200px"
                          {...register(`${path}.experiences.${idx}.bullets` as const)}
                          bg="surface.card"
                          borderColor="border.muted"
                          _hover={{ borderColor: 'brand.300' }}
                        />
                        <Button leftIcon={<Icon as={FiTrash2} />} colorScheme="red" variant="ghost" alignSelf="flex-start" onClick={() => removeExperience(idx)}>
                          Remove Role
                        </Button>
                      </Stack>
                    </TabPanel>
                  ))}
                </TabPanels>
              ) : (
                <Box mt={4}>
                  <Text fontSize="sm" color="text.muted" mb={3}>
                    Start by adding your first role.
                  </Text>
                  <Button
                    leftIcon={<Icon as={FiPlus} />}
                    onClick={() =>
                      appendExperience({
                        role: '',
                        company: '',
                        location: '',
                        date_range: '',
                        bullets: '',
                      })
                    }
                    colorScheme="brand"
                  >
                    Add Role
                  </Button>
                </Box>
              )}
            </Tabs>
          </Stack>
        )}

        {kind === SectionKind.Generic && (
          <Stack spacing={4}>
            <Textarea
              placeholder="Paragraphs (separate with blank lines)"
              minH="120px"
              {...register(`${path}.paragraphs` as const)}
              bg="surface.card"
              borderColor="border.muted"
              _hover={{ borderColor: 'brand.300' }}
            />
            <Textarea
              placeholder="Bullets (one per line)"
              minH="120px"
              {...register(`${path}.bullets` as const)}
              bg="surface.card"
              borderColor="border.muted"
              _hover={{ borderColor: 'brand.300' }}
            />
          </Stack>
        )}

        {kind !== SectionKind.Summary && kind !== SectionKind.TechnicalSkills && kind !== SectionKind.Experience && kind !== SectionKind.Generic && (
          <Stack spacing={4}>
            <Textarea
              placeholder="Paragraphs (separate with blank lines)"
              minH="120px"
              {...register(`${path}.paragraphs` as const)}
              bg="surface.card"
              borderColor="border.muted"
              _hover={{ borderColor: 'brand.300' }}
            />
            <Textarea
              placeholder="Bullets (one per line)"
              minH="120px"
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
