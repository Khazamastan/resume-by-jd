import {
  AspectRatio,
  Badge,
  Box,
  Button,
  ButtonGroup,
  Center,
  Heading,
  HStack,
  Icon,
  Spinner,
  Stack,
  Text,
  useBreakpointValue,
  VStack,
} from '@chakra-ui/react';
import { FiDownload, FiExternalLink, FiFileText, FiPenTool } from 'react-icons/fi';
import { useCallback } from 'react';

import { usePdfUrl } from '@/features/shared/usePdfUrl';

interface ResumePreviewProps {
  pdfBase64: string | null;
  isLoading: boolean;
  downloadFileName: string;
  profileName?: string;
  onEdit?: () => void;
}

export function ResumePreview({
  pdfBase64,
  isLoading,
  downloadFileName,
  profileName,
  onEdit,
}: ResumePreviewProps) {
  const pdfUrl = usePdfUrl(pdfBase64);
  const aspect = useBreakpointValue({ base: 3 / 4, md: 210 / 297 }) ?? 210 / 297;

  const handleDownload = useCallback(() => {
    if (!pdfUrl) {
      return;
    }
    const anchor = document.createElement('a');
    anchor.href = pdfUrl;
    anchor.download = downloadFileName;
    anchor.click();
  }, [downloadFileName, pdfUrl]);

  const handleOpenNewTab = useCallback(() => {
    if (!pdfUrl) {
      return;
    }
    window.open(pdfUrl, '_blank', 'noopener,noreferrer');
  }, [pdfUrl]);

  return (
    <Stack
      spacing={6}
      h="full"
      bg="surface.card"
      border="1px solid"
      borderColor="border.muted"
      borderRadius="2xl"
      p={{ base: 6, md: 8 }}
      boxShadow="md"
    >
      <HStack justify="space-between" align="flex-start">
        <VStack align="flex-start" spacing={2}>
          <Heading fontSize="xl" fontWeight="semibold">
            Preview &amp; Download
          </Heading>
          <HStack spacing={2}>
            <Badge colorScheme={pdfUrl ? 'green' : 'yellow'} variant="subtle">
              {pdfUrl ? 'Up to date' : 'Awaiting generation'}
            </Badge>
            {profileName && (
              <Text color="text.subtle" fontSize="sm">
                {profileName}
              </Text>
            )}
          </HStack>
          <Text color="text.subtle" fontSize="sm">
            {pdfUrl
              ? 'Download the current PDF or jump back into the editor to refine.'
              : 'Generate a resume to unlock the live preview and editing tools.'}
          </Text>
        </VStack>
        {onEdit && (
          <ButtonGroup>
            <Button leftIcon={<Icon as={FiPenTool} />} variant="outline" colorScheme="brand" onClick={onEdit}>
              Open Editor
            </Button>
          </ButtonGroup>
        )}
      </HStack>

      <Box flex="1" rounded="xl" overflow="hidden" position="relative" border="1px solid" borderColor="border.muted" bg="surface.subtle">
        <AspectRatio ratio={aspect}>
          <>
            {pdfUrl ? (
              <iframe
                title="Resume preview"
                src={pdfUrl}
                style={{ width: '100%', height: '100%', border: 'none' }}
                aria-label="Generated resume preview"
              />
            ) : (
              <Center h="full" flexDir="column" gap={3} bg="surface.card" px={6}>
                <Icon as={FiFileText} boxSize={10} color="text.muted" />
                <Text color="text.muted" textAlign="center" maxW="320px">
                  Your generated resume will appear here. Upload a reference resume and profile to begin.
                </Text>
                <Text color="text.muted" fontSize="sm">
                  Step 1: Use the panel on the left to upload your files.
                </Text>
              </Center>
            )}
          </>
        </AspectRatio>
        {isLoading && (
          <Center position="absolute" inset={0} bg="rgba(255,255,255,0.7)" backdropFilter="blur(2px)">
            <Spinner size="xl" color="brand.500" thickness="4px" />
          </Center>
        )}
      </Box>

      <HStack spacing={3} justify="flex-end" flexWrap="wrap">
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
          onClick={handleDownload}
          isDisabled={!pdfUrl}
        >
          Download
        </Button>
      </HStack>
    </Stack>
  );
}
