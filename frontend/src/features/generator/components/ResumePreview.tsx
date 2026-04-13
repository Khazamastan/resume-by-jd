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
import { useEffect, useState } from 'react';
import { FiFileText, FiPenTool } from 'react-icons/fi';

import { usePdfUrl } from '@/features/shared/usePdfUrl';

interface ResumePreviewProps {
  pdfBase64: string | null;
  isLoading: boolean;
  profileName?: string;
  onEdit?: () => void;
}

export function ResumePreview({
  pdfBase64,
  isLoading,
  profileName,
  onEdit,
}: ResumePreviewProps) {
  const pdfUrl = usePdfUrl(pdfBase64);
  const aspect = useBreakpointValue({ base: 3 / 4, md: 210 / 297 }) ?? 210 / 297;
  const [isPdfFrameLoading, setIsPdfFrameLoading] = useState<boolean>(Boolean(pdfUrl));

  useEffect(() => {
    setIsPdfFrameLoading(Boolean(pdfUrl));
  }, [pdfUrl]);

  const showLoader = pdfUrl ? isPdfFrameLoading : isLoading;

  return (
    <Stack
      spacing={4}
      bg="surface.card"
      border="1px solid"
      borderColor="border.muted"
      borderRadius="xl"
      p={{ base: 4, md: 5 }}
      boxShadow="md"
    >
      <HStack justify="space-between" align="flex-start">
        <VStack align="flex-start" spacing={1}>
          <Heading fontSize="lg" fontWeight="semibold">
            Preview
          </Heading>
          <HStack spacing={2}>
            <Badge colorScheme="brand" variant={pdfUrl ? 'subtle' : 'outline'}>
              {pdfUrl ? 'Up to date' : 'Awaiting generation'}
            </Badge>
            {profileName && (
              <Text color="text.subtle" fontSize="sm">
                {profileName}
              </Text>
            )}
          </HStack>
          <Text color="text.subtle" fontSize="xs">
            {pdfUrl
              ? 'Review the current PDF and jump back into the editor to refine.'
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

      <Box
        w="full"
        maxW={{ base: '100%', xl: '1160px' }}
        mx="auto"
        rounded="lg"
        overflow="hidden"
        position="relative"
        border="1px solid"
        borderColor="border.muted"
        bg="surface.subtle"
      >
        <AspectRatio ratio={aspect}>
          <>
            {pdfUrl ? (
              <iframe
                key={pdfUrl}
                title="Resume preview"
                src={pdfUrl}
                style={{ width: '100%', height: '100%', border: 'none' }}
                aria-label="Generated resume preview"
                onLoad={() => setIsPdfFrameLoading(false)}
                onError={() => setIsPdfFrameLoading(false)}
              />
            ) : (
              <Center h="full" flexDir="column" gap={2} bg="surface.card" px={5}>
                <Icon as={FiFileText} boxSize={10} color="text.muted" />
                <Text color="text.muted" textAlign="center" maxW="320px">
                  Your generated resume will appear here. You can upload files, or generate using default project files.
                </Text>
                <Text color="text.muted" fontSize="xs">
                  Step 1: Click Generate Resume (uploads are optional).
                </Text>
              </Center>
            )}
          </>
        </AspectRatio>
        {showLoader && (
          <Center position="absolute" inset={0} bg="rgba(255,255,255,0.7)" backdropFilter="blur(2px)">
            <Spinner size="xl" color="brand.500" thickness="4px" transform={{ base: 'translateY(-12px)', md: 'translateY(-18px)' }} />
          </Center>
        )}
      </Box>
    </Stack>
  );
}
