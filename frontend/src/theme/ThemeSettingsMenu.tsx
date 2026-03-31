import {
  Box,
  HStack,
  Icon,
  IconButton,
  Menu,
  MenuButton,
  MenuGroup,
  MenuItem,
  MenuList,
  Stack,
  Text,
  Tooltip,
  useColorMode,
} from '@chakra-ui/react';
import { FiCheck, FiMoon, FiSettings, FiSun } from 'react-icons/fi';

import { useThemeSettings } from './ThemeSettingsProvider';

export function ThemeSettingsMenu() {
  const { colorMode, toggleColorMode } = useColorMode();
  const isLight = colorMode === 'light';
  const { accent, setAccent, accentOptions } = useThemeSettings();

  return (
    <Menu placement="bottom-end">
      <Tooltip label="Theme settings" hasArrow>
        <MenuButton
          as={IconButton}
          variant="ghost"
          aria-label="Theme settings"
          icon={<Icon as={FiSettings} />}
        />
      </Tooltip>
      <MenuList>
        <MenuGroup title="Color mode">
          <MenuItem icon={<Icon as={isLight ? FiMoon : FiSun} />} onClick={toggleColorMode}>
            Switch to {isLight ? 'Dark' : 'Light'} mode
          </MenuItem>
        </MenuGroup>
        <MenuGroup title="Accent">
          <Stack spacing={2} px={2} py={1}>
            {accentOptions.map((option) => {
              const isActive = accent === option.key;
              return (
                <MenuItem
                  key={option.key}
                  onClick={() => setAccent(option.key)}
                  icon={isActive ? <Icon as={FiCheck} /> : <Box boxSize={3} borderRadius="full" bg={option.swatch} />}
                  closeOnSelect
                >
                  <HStack spacing={3}>
                    <Box boxSize={4} borderRadius="full" bg={option.swatch} />
                    <Stack spacing={0}>
                      <Text fontWeight="semibold">{option.label}</Text>
                      <Text fontSize="xs" color="text.muted">
                        {option.description}
                      </Text>
                    </Stack>
                  </HStack>
                </MenuItem>
              );
            })}
          </Stack>
        </MenuGroup>
      </MenuList>
    </Menu>
  );
}
