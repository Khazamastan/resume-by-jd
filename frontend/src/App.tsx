import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Badge,
  Box,
  Button,
  ButtonGroup,
  Flex,
  Grid,
  Heading,
  HStack,
  Icon,
  Stack,
  Text,
  useDisclosure,
  useToast,
  VStack,
} from '@chakra-ui/react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { FiArrowRight, FiDownload, FiExternalLink, FiRefreshCcw } from 'react-icons/fi';

import { EditResumeModal } from '@/features/editor/components/EditResumeModal';
import { buildDownloadName, defaultSampleProfileId, GenerateResumeParams } from '@/features/generator/api';
import { GeneratorForm } from '@/features/generator/components/GeneratorForm';
import { ResumePreview } from '@/features/generator/components/ResumePreview';
import { useResumeSession } from '@/features/generator/useResumeSession';
import { usePdfUrl } from '@/features/shared/usePdfUrl';
import type { ResumeSection } from '@/features/shared/types';
import { ThemeSettingsMenu } from '@/theme/ThemeSettingsMenu';

interface AppHeaderProps {
  hasSession: boolean;
  onEdit?: () => void;
  onReset?: () => void;
}

function AppHeader({ hasSession, onEdit, onReset }: AppHeaderProps) {
  return (
    <Flex
      as="header"
      align="center"
      justify="space-between"
      px={{ base: 4, md: 6 }}
      py={3}
      borderBottomWidth="1px"
      borderColor="border.muted"
      bg="surface.card"
    >
      <VStack align="flex-start" spacing={0}>
        <Heading
          fontSize={{ base: 'xl', md: '2xl' }}
          fontWeight="black"
          letterSpacing="wide"
          bgGradient="linear(to-r, brand.300, brand.100)"
          bgClip="text"
        >
          Resume Studio
        </Heading>
        <Text color="text.subtle" fontSize="xs">
          Generate, review, and tailor a job-ready resume in one flow.
        </Text>
      </VStack>
      <ButtonGroup spacing={2} variant="outline">
        {hasSession && onEdit && (
          <Button
            leftIcon={<Icon as={FiArrowRight} />}
            colorScheme="brand"
            variant="solid"
            onClick={onEdit}
          >
            Open Editor
          </Button>
        )}
        {hasSession && onReset && (
          <Button leftIcon={<Icon as={FiRefreshCcw} />} onClick={onReset} colorScheme="red" variant="ghost">
            Reset Session
          </Button>
        )}
        <Button
          as="a"
          href="https://docs.netlify.com/"
          target="_blank"
          rel="noopener noreferrer"
          variant="ghost"
          colorScheme="gray"
        >
          Netlify Docs
        </Button>
        <ThemeSettingsMenu />
      </ButtonGroup>
    </Flex>
  );
}

function SessionStatusBanner({ isUpdating }: { isUpdating: boolean }) {
  if (!isUpdating) {
    return null;
  }

  const title = 'Applying updates';
  const description = 'Refreshing the preview with your latest edits.';

  return (
    <Alert
      status="info"
      variant="left-accent"
      borderRadius="lg"
      borderLeftWidth="4px"
      bg="surface.subtle"
      borderColor="brand.400"
      color="text.subtle"
    >
      <AlertIcon color="brand.500" />
      <Stack spacing={1}>
        <AlertTitle fontSize="sm" textTransform="uppercase" letterSpacing="wide" color="brand.700">
          {title}
        </AlertTitle>
        <AlertDescription fontSize="sm" color="text.subtle">
          {description}
        </AlertDescription>
      </Stack>
    </Alert>
  );
}

interface SessionSummaryProps {
  profileName?: string;
  headline?: string;
  sections: ResumeSection[];
  onEdit: () => void;
  onReset: () => void;
  isBusy: boolean;
}

function SessionSummary({ profileName, headline, sections, onEdit, onReset, isBusy }: SessionSummaryProps) {
  const visibleSections = sections.slice(0, 4);

  return (
    <Stack
      spacing={4}
      w="full"
      maxW={{ base: '100%', xl: '400px' }}
      alignSelf="center"
      border="1px solid"
      borderColor="border.muted"
      borderRadius="xl"
      p={{ base: 4, md: 5 }}
      bg="surface.card"
      boxShadow="sm"
    >
      <VStack align="flex-start" spacing={1}>
        <Heading fontSize="lg">Current Resume</Heading>
        <Text fontSize="sm" color="text.subtle">
          Quickly access the editor or start a fresh session.
        </Text>
      </VStack>

      <Stack spacing={2}>
        {profileName && (
          <Text fontWeight="semibold" fontSize="md">
            {profileName}
          </Text>
        )}
        {headline && (
          <Text fontSize="sm" color="text.subtle">
            {headline}
          </Text>
        )}
        <Badge width="fit-content" colorScheme="brand">
          {sections.length} sections
        </Badge>
      </Stack>

      {sections.length > 0 && (
        <Stack spacing={2}>
          <Text fontSize="xs" textTransform="uppercase" letterSpacing="wide" color="text.muted">
            Sections included
          </Text>
          <Stack spacing={1}>
            {visibleSections.map((section) => (
              <Text key={section.title} fontSize="sm" color="text.subtle">
                ■ {section.title}
              </Text>
            ))}
            {sections.length > visibleSections.length && (
              <Text fontSize="sm" color="text.muted">
                + {sections.length - visibleSections.length} more
              </Text>
            )}
          </Stack>
        </Stack>
      )}

      <ButtonGroup spacing={2} flexWrap="wrap">
        <Button leftIcon={<Icon as={FiArrowRight} />} colorScheme="brand" onClick={onEdit} isDisabled={isBusy}>
          Open Editor
        </Button>
        <Button
          leftIcon={<Icon as={FiRefreshCcw} />}
          variant="ghost"
          colorScheme="red"
          onClick={onReset}
          isDisabled={isBusy}
        >
          Reset Session
        </Button>
      </ButtonGroup>
    </Stack>
  );
}

export default function App() {
  const toast = useToast();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { session, generate, isGenerating, generateError, reset, isUpdating, update, updateError } = useResumeSession();
  const hasAutoBootstrapped = useRef(false);
  const [isGenerateButtonLoading, setIsGenerateButtonLoading] = useState(false);
  const pdfUrl = usePdfUrl(session?.pdf ?? null);

  useEffect(() => {
    if (generateError) {
      toast({
        title: 'Generation failed',
        description: generateError instanceof Error ? generateError.message : 'Unknown error',
        status: 'error',
      });
    }
  }, [generateError, toast]);

  useEffect(() => {
    if (updateError) {
      toast({
        title: 'Update failed',
        description: updateError instanceof Error ? updateError.message : 'Unknown error',
        status: 'error',
      });
    }
  }, [updateError, toast]);

  useEffect(() => {
    if (hasAutoBootstrapped.current) {
      return;
    }
    if (session || isGenerating || isUpdating) {
      return;
    }
    hasAutoBootstrapped.current = true;
    generate({ sampleProfile: defaultSampleProfileId }).catch(() => undefined);
  }, [generate, isGenerating, isUpdating, session]);

  const handleGenerate = useCallback(
    async (params: GenerateResumeParams) => {
      setIsGenerateButtonLoading(true);
      try {
        await generate(params);
        toast({
          title: 'Resume generated',
          description: 'Preview refreshed with the latest document.',
          status: 'success',
          duration: 3000,
        });
      } finally {
        setIsGenerateButtonLoading(false);
      }
    },
    [generate, toast],
  );

  const handleReset = useCallback(() => {
    reset();
    toast({
      title: 'Session cleared',
      description: 'Generate again with uploads, or rely on the selected sample profile files.',
      status: 'info',
      duration: 3000,
    });
  }, [reset, toast]);

  const downloadName = buildDownloadName(session?.profile?.name);
  const hasSession = Boolean(session);
  const generatorFormId = 'generator-form';

  const handleOpenNewTab = useCallback(() => {
    if (!pdfUrl) {
      return;
    }
    window.open(pdfUrl, '_blank', 'noopener,noreferrer');
  }, [pdfUrl]);

  const handleDownload = useCallback(() => {
    if (!pdfUrl) {
      return;
    }
    const anchor = document.createElement('a');
    anchor.href = pdfUrl;
    anchor.download = downloadName;
    anchor.click();
  }, [downloadName, pdfUrl]);

  return (
    <Flex direction="column" minH="100vh" bgGradient="linear(to-b, surface.canvas, surface.subtle)">
      <AppHeader hasSession={hasSession} onEdit={hasSession ? onOpen : undefined} onReset={hasSession ? handleReset : undefined} />
      <Box as="main" flex="1" py={6} pb={{ base: 24, md: 20 }}>
        <Box w="full" px={{ base: 4, md: 6 }}>
          <Stack spacing={5}>
            <SessionStatusBanner isUpdating={isUpdating} />
            <Box w="full" maxW={{ base: '100%', xl: '1660px' }} mx="auto">
              <Grid templateColumns={{ base: '1fr', xl: '400px minmax(0, 1fr)' }} gap={{ base: 4, xl: 3 }} alignItems="start">
                <Stack spacing={4} w="full" maxW={{ base: '100%', xl: '400px' }} mx={{ base: 0, xl: 'auto' }}>
                  <GeneratorForm formId={generatorFormId} onGenerate={handleGenerate} isGenerating={isGenerating} />
                  {session && (
                    <SessionSummary
                      profileName={session.profile?.name}
                      headline={session.profile?.headline}
                      sections={session.sections}
                      onEdit={onOpen}
                      onReset={handleReset}
                      isBusy={isGenerating || isUpdating}
                    />
                  )}
                </Stack>
                <Box w="full" maxW={{ base: '100%', xl: '1240px' }} mx={{ base: 0, xl: 'auto' }}>
                  <ResumePreview
                    pdfBase64={session?.pdf ?? null}
                    isLoading={isGenerating || isUpdating}
                    profileName={session?.profile?.name}
                    onEdit={session ? onOpen : undefined}
                  />
                </Box>
              </Grid>
            </Box>
          </Stack>
        </Box>
      </Box>
      <Box
        as="footer"
        position="fixed"
        bottom={0}
        left={0}
        right={0}
        borderTopWidth="1px"
        borderColor="border.muted"
        bg="surface.card"
        zIndex={20}
      >
        <Box w="full" px={{ base: 4, md: 6 }} py={2}>
          <HStack spacing={2} justify="flex-end" flexWrap="wrap">
            <Button
              type="submit"
              form={generatorFormId}
              colorScheme="brand"
              isLoading={isGenerateButtonLoading}
              isDisabled={isUpdating || isGenerateButtonLoading}
            >
              Generate
            </Button>
            <Button
              leftIcon={<Icon as={FiExternalLink} />}
              variant="ghost"
              colorScheme="gray"
              onClick={handleOpenNewTab}
              isDisabled={!pdfUrl}
            >
              Open in new tab
            </Button>
            <Button
              leftIcon={<Icon as={FiDownload} />}
              colorScheme="brand"
              variant="outline"
              onClick={handleDownload}
              isDisabled={!pdfUrl}
            >
              Download
            </Button>
          </HStack>
        </Box>
      </Box>
      <EditResumeModal isOpen={isOpen} onClose={onClose} session={session} onUpdated={update} isUpdating={isUpdating} />
    </Flex>
  );
}
