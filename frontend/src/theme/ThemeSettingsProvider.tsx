import { ChakraProvider, ColorModeScript } from '@chakra-ui/react';
import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { AccentKey, type AccentOption,accentOptions, createAppTheme, defaultAccent } from './index';

interface ThemeSettingsContextValue {
  accent: AccentKey;
  setAccent: (accent: AccentKey) => void;
  accentOptions: AccentOption[];
}

const ThemeSettingsContext = createContext<ThemeSettingsContextValue | undefined>(undefined);

const ACCENT_STORAGE_KEY = 'resume-theme-accent';

function getStoredAccent(): AccentKey | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const stored = window.localStorage.getItem(ACCENT_STORAGE_KEY) as AccentKey | null;
  if (stored && accentOptions.some((option) => option.key === stored)) {
    return stored;
  }
  return null;
}

export function ThemeSettingsProvider({ children }: PropsWithChildren) {
  const [accent, setAccentState] = useState<AccentKey>(() => getStoredAccent() ?? defaultAccent);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(ACCENT_STORAGE_KEY, accent);
    }
  }, [accent]);

  const setAccent = useCallback((next: AccentKey) => {
    setAccentState(next);
  }, []);

  const theme = useMemo(() => createAppTheme(accent), [accent]);

  const value = useMemo<ThemeSettingsContextValue>(
    () => ({
      accent,
      setAccent,
      accentOptions,
    }),
    [accent, setAccent],
  );

  return (
    <ThemeSettingsContext.Provider value={value}>
      <ChakraProvider theme={theme}>
        <ColorModeScript initialColorMode={theme.config.initialColorMode} />
        {children}
      </ChakraProvider>
    </ThemeSettingsContext.Provider>
  );
}

export function useThemeSettings() {
  const ctx = useContext(ThemeSettingsContext);
  if (!ctx) {
    throw new Error('useThemeSettings must be used within a ThemeSettingsProvider');
  }
  return ctx;
}
