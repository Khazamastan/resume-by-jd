import { extendTheme, ThemeConfig } from '@chakra-ui/react';

export type AccentKey = 'indigo' | 'teal' | 'orange';

export interface AccentOption {
  key: AccentKey;
  label: string;
  description: string;
  swatch: string;
}

const config: ThemeConfig = {
  initialColorMode: 'light',
  useSystemColorMode: true,
};

const accentPalettes: Record<AccentKey, Record<number, string>> = {
  indigo: {
    50: '#eef2ff',
    100: '#e0e7ff',
    200: '#c7d2fe',
    300: '#a5b4fc',
    400: '#818cf8',
    500: '#6366f1',
    600: '#4f46e5',
    700: '#4338ca',
    800: '#312e81',
    900: '#1e1b4b',
  },
  teal: {
    50: '#f0fdfa',
    100: '#ccfbf1',
    200: '#99f6e4',
    300: '#5eead4',
    400: '#2dd4bf',
    500: '#14b8a6',
    600: '#0d9488',
    700: '#0f766e',
    800: '#115e59',
    900: '#134e4a',
  },
  orange: {
    50: '#fff7ed',
    100: '#ffedd5',
    200: '#fed7aa',
    300: '#fdba74',
    400: '#fb923c',
    500: '#f97316',
    600: '#ea580c',
    700: '#c2410c',
    800: '#9a3412',
    900: '#7c2d12',
  },
};

export const accentOptions: AccentOption[] = [
  {
    key: 'indigo',
    label: 'Indigo',
    description: 'Balanced, professional palette suited for most roles.',
    swatch: accentPalettes.indigo[500],
  },
  {
    key: 'teal',
    label: 'Teal',
    description: 'Fresh, modern palette ideal for product and design roles.',
    swatch: accentPalettes.teal[500],
  },
  {
    key: 'orange',
    label: 'Orange',
    description: 'Warm, energetic palette great for customer-facing roles.',
    swatch: accentPalettes.orange[500],
  },
];

export const defaultAccent: AccentKey = 'indigo';

const baseThemeConfig = {
  config,
  fonts: {
    heading: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    body: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  },
  semanticTokens: {
    colors: {
      'surface.canvas': { default: 'gray.50', _dark: 'gray.900' },
      'surface.card': { default: 'white', _dark: 'gray.800' },
      'surface.subtle': { default: 'gray.100', _dark: 'gray.700' },
      'surface.muted': { default: 'gray.200', _dark: 'gray.600' },
      'text.primary': { default: 'gray.800', _dark: 'gray.100' },
      'text.subtle': { default: 'gray.600', _dark: 'gray.300' },
      'text.muted': { default: 'gray.500', _dark: 'gray.400' },
      'border.muted': { default: 'gray.200', _dark: 'whiteAlpha.200' },
      'shadow.lg': { default: 'rgba(17, 24, 39, 0.12)', _dark: 'rgba(15, 23, 42, 0.45)' },
    },
  },
  components: {
    Button: {
      baseStyle: {
        fontWeight: '600',
        borderRadius: 'lg',
      },
      defaultProps: {
        colorScheme: 'brand',
      },
    },
    Badge: {
      baseStyle: {
        textTransform: 'none',
        borderRadius: 'full',
        fontWeight: '600',
        letterSpacing: 'wide',
      },
    },
    Input: {
      defaultProps: {
        focusBorderColor: 'brand.400',
      },
      sizes: {
        md: {
          field: {
            borderRadius: 'lg',
          },
        },
      },
    },
    Textarea: {
      defaultProps: {
        focusBorderColor: 'brand.400',
      },
      sizes: {
        md: {
          borderRadius: 'lg',
        },
      },
    },
    Tabs: {
      baseStyle: {
        tab: {
          fontWeight: '600',
        },
      },
    },
    Modal: {
      baseStyle: {
        dialog: {
          borderRadius: '2xl',
        },
      },
    },
    Alert: {
      baseStyle: {
        container: {
          borderRadius: 'xl',
          alignItems: 'flex-start',
        },
      },
    },
  },
  styles: {
    global: {
      body: {
        bg: 'surface.canvas',
        color: 'text.primary',
        minHeight: '100vh',
      },
      'html, body, #root': {
        height: '100%',
      },
    },
  },
};

export function createAppTheme(accent: AccentKey = defaultAccent) {
  return extendTheme({
    ...baseThemeConfig,
    colors: {
      brand: accentPalettes[accent],
    },
  });
}
