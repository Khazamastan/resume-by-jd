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
  Heading,
  Icon,
  SimpleGrid,
  Stack,
  Text,
  useDisclosure,
  useToast,
  VStack,
} from '@chakra-ui/react';
import { useCallback, useEffect } from 'react';
import { FiArrowRight, FiRefreshCcw } from 'react-icons/fi';

import { EditResumeModal } from '@/features/editor/components/EditResumeModal';
import { buildDownloadName, GenerateResumeParams } from '@/features/generator/api';
import { GeneratorForm } from '@/features/generator/components/GeneratorForm';
import { ResumePreview } from '@/features/generator/components/ResumePreview';
import { useResumeSession } from '@/features/generator/useResumeSession';
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
      px={{ base: 6, md: 10 }}
      py={6}
      borderBottomWidth="1px"
      borderColor="border.muted"
      bg="surface.card"
    >
      <VStack align="flex-start" spacing={0}>
        <Heading
          fontSize={{ base: '2xl', md: '3xl' }}
          fontWeight="black"
          letterSpacing="wide"
          bgGradient="linear(to-r, brand.300, brand.100)"
          bgClip="text"
        >
          Resume Studio
        </Heading>
        <Text color="text.subtle" fontSize="sm">
          Generate, review, and tailor a job-ready resume in one flow.
        </Text>
      </VStack>
      <ButtonGroup spacing={3} variant="outline">
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

function SessionStatusBanner({ isGenerating, isUpdating }: { isGenerating: boolean; isUpdating: boolean }) {
  if (!isGenerating && !isUpdating) {
    return null;
  }

  const title = isGenerating ? 'Generating resume' : 'Applying updates';
  const description = isGenerating
    ? 'Hang tight while we tailor the PDF to your job description.'
    : 'Refreshing the preview with your latest edits.';

  return (
    <Alert
      status="info"
      variant="left-accent"
      borderRadius="2xl"
      borderLeftWidth="6px"
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
      spacing={5}
      border="1px solid"
      borderColor="border.muted"
      borderRadius="2xl"
      p={{ base: 5, md: 6 }}
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

      <ButtonGroup spacing={3} flexWrap="wrap">
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

  const handleGenerate = useCallback(
    async (params: GenerateResumeParams) => {
      await generate(params);
      toast({
        title: 'Resume generated',
        description: 'Preview refreshed with the latest document.',
        status: 'success',
        duration: 3000,
      });
    },
    [generate, toast],
  );

  const handleReset = useCallback(() => {
    reset();
    toast({
      title: 'Session cleared',
      description: 'Upload a new reference (and optionally a profile) to get started again.',
      status: 'info',
      duration: 3000,
    });
  }, [reset, toast]);

  const downloadName = buildDownloadName(session?.profile?.name);
  const hasSession = Boolean(session);

  return (
    <Flex direction="column" minH="100vh" bgGradient="linear(to-b, surface.canvas, surface.subtle)">
      <AppHeader hasSession={hasSession} onEdit={hasSession ? onOpen : undefined} onReset={hasSession ? handleReset : undefined} />
      <Box as="main" flex="1" py={10}>
        <Box maxW="1280px" mx="auto" px={{ base: 6, md: 10 }}>
          <Stack spacing={8}>
            <SessionStatusBanner isGenerating={isGenerating} isUpdating={isUpdating} />
            <SimpleGrid columns={{ base: 1, xl: 3 }} spacing={{ base: 6, xl: 10 }}>
              <Stack spacing={6} gridColumn={{ base: 'span 1', xl: 'span 1' }}>
                <GeneratorForm onGenerate={handleGenerate} isGenerating={isGenerating} />
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
              <Box gridColumn={{ base: 'span 1', xl: 'span 2' }}>
                <ResumePreview
                  pdfBase64={session?.pdf ?? null}
                  isLoading={isGenerating || isUpdating}
                  downloadFileName={downloadName}
                  profileName={session?.profile?.name}
                  onEdit={session ? onOpen : undefined}
                />
              </Box>
            </SimpleGrid>
          </Stack>
        </Box>
      </Box>
      <EditResumeModal isOpen={isOpen} onClose={onClose} session={session} onUpdated={update} isUpdating={isUpdating} />
    </Flex>
  );
}
