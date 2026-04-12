import { extendTheme, ThemeConfig } from '@chakra-ui/react';

export type AccentKey =
  | 'reference'
  | 'indigo'
  | 'teal'
  | 'orange'
  | 'blue'
  | 'black'
  | 'gray'
  | 'lightGray'
  | 'darkBlue'
  | 'jet'
  | 'royalPurple'
  | 'darkCornflowerBlue'
  | 'egyptianBlue'
  | 'slateGray'
  | 'blueGray'
  | 'blueGreen'
  | 'viridianGreen'
  | 'opal'
  | 'darkSeaGreen'
  | 'fernGreen'
  | 'castletonGreen'
  | 'bronze'
  | 'kobe'
  | 'upMaroon'
  | 'downToEarth'
  | 'sophisticatedPinks'
  | 'forestHues'
  | 'blueOrange'
  | 'navyGold'
  | 'redGray'
  | 'boldBright'
  | 'minimalist'
  | 'orangeBlue'
  | 'warmNeutral'
  | 'royalPurpleBlue'
  | 'rosyCharm';

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

function normalizeHex(hex: string): string {
  let value = hex.trim();
  if (!value.startsWith('#')) {
    value = `#${value}`;
  }
  if (value.length === 4) {
    value = `#${value[1]}${value[1]}${value[2]}${value[2]}${value[3]}${value[3]}`;
  }
  return value.toLowerCase();
}

function hexToRgb(hex: string): [number, number, number] {
  const normalized = normalizeHex(hex);
  const r = parseInt(normalized.slice(1, 3), 16);
  const g = parseInt(normalized.slice(3, 5), 16);
  const b = parseInt(normalized.slice(5, 7), 16);
  return [r, g, b];
}

function mixHex(base: string, target: string, amount: number): string {
  const [r1, g1, b1] = hexToRgb(base);
  const [r2, g2, b2] = hexToRgb(target);
  const mix = (v1: number, v2: number) => Math.round(v1 + (v2 - v1) * amount);
  const r = mix(r1, r2);
  const g = mix(g1, g2);
  const b = mix(b1, b2);
  const toHex = (value: number) => value.toString(16).padStart(2, '0');
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

function createAccentPalette(base: string): Record<number, string> {
  const normalized = normalizeHex(base);
  return {
    50: mixHex(normalized, '#ffffff', 0.85),
    100: mixHex(normalized, '#ffffff', 0.7),
    200: mixHex(normalized, '#ffffff', 0.55),
    300: mixHex(normalized, '#ffffff', 0.4),
    400: mixHex(normalized, '#ffffff', 0.25),
    500: normalized,
    600: mixHex(normalized, '#000000', 0.15),
    700: mixHex(normalized, '#000000', 0.3),
    800: mixHex(normalized, '#000000', 0.45),
    900: mixHex(normalized, '#000000', 0.6),
  };
}

const accentBases: Record<AccentKey, string> = {
  reference: '#10b981',
  indigo: '#6366f1',
  teal: '#14b8a6',
  orange: '#f97316',
  blue: '#3b82f6',
  black: '#404040',
  gray: '#71717a',
  lightGray: '#6b7280',
  darkBlue: '#1f74ff',
  jet: '#2A2D31',
  royalPurple: '#6F5392',
  darkCornflowerBlue: '#2C446F',
  egyptianBlue: '#20349F',
  slateGray: '#6C7F93',
  blueGray: '#799ACC',
  blueGreen: '#359EBF',
  viridianGreen: '#468F92',
  opal: '#B2D1C9',
  darkSeaGreen: '#90AE85',
  fernGreen: '#647C41',
  castletonGreen: '#005842',
  bronze: '#CD853F',
  kobe: '#7A3516',
  upMaroon: '#770B0E',
  downToEarth: '#2B2D36',
  sophisticatedPinks: '#B23A73',
  forestHues: '#274031',
  blueOrange: '#0E5A86',
  navyGold: '#0D0F1F',
  redGray: '#D23B3B',
  boldBright: '#FF7E21',
  minimalist: '#3C4B52',
  orangeBlue: '#E6722C',
  warmNeutral: '#C2726A',
  royalPurpleBlue: '#3C3E8C',
  rosyCharm: '#E7BAC8',
};

const accentPalettes: Record<AccentKey, Record<number, string>> = Object.fromEntries(
  Object.entries(accentBases).map(([key, base]) => [key, createAccentPalette(base)]),
) as Record<AccentKey, Record<number, string>>;

export const accentOptions: AccentOption[] = [
  {
    key: 'reference',
    label: 'Reference Accent',
    description: 'Uses the accent extracted from your reference resume (recommended).',
    swatch: accentPalettes.reference[500],
  },
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
  {
    key: 'blue',
    label: 'Blue',
    description: 'Confident and vibrant blue for tech-forward roles.',
    swatch: accentPalettes.blue[500],
  },
  {
    key: 'black',
    label: 'Black',
    description: 'High-contrast monochrome accent for executive resumes.',
    swatch: accentPalettes.black[600],
  },
  {
    key: 'gray',
    label: 'Gray',
    description: 'Neutral gray palette that keeps focus on content.',
    swatch: accentPalettes.gray[500],
  },
  {
    key: 'lightGray',
    label: 'Light Gray',
    description: 'Soft gray accent for minimalist layouts.',
    swatch: accentPalettes.lightGray[400],
  },
  {
    key: 'darkBlue',
    label: 'Dark Blue',
    description: 'Deep navy tone suited for formal presentations.',
    swatch: accentPalettes.darkBlue[600],
  },
  {
    key: 'jet',
    label: 'Jet',
    description: 'Modern charcoal tone with strong contrast.',
    swatch: accentPalettes.jet[500],
  },
  {
    key: 'royalPurple',
    label: 'Royal Purple',
    description: 'Sophisticated purple perfect for creative roles.',
    swatch: accentPalettes.royalPurple[500],
  },
  {
    key: 'darkCornflowerBlue',
    label: 'Dark Cornflower Blue',
    description: 'Rich blue with a polished, executive feel.',
    swatch: accentPalettes.darkCornflowerBlue[500],
  },
  {
    key: 'egyptianBlue',
    label: 'Egyptian Blue',
    description: 'Vibrant blue inspired by classical palettes.',
    swatch: accentPalettes.egyptianBlue[500],
  },
  {
    key: 'slateGray',
    label: 'Slate Gray',
    description: 'Cool gray with a calm, technical aesthetic.',
    swatch: accentPalettes.slateGray[500],
  },
  {
    key: 'blueGray',
    label: 'Blue Gray',
    description: 'Soft blue-gray ideal for minimalist layouts.',
    swatch: accentPalettes.blueGray[500],
  },
  {
    key: 'blueGreen',
    label: 'Blue Green',
    description: 'Balanced teal-blue with modern energy.',
    swatch: accentPalettes.blueGreen[500],
  },
  {
    key: 'viridianGreen',
    label: 'Viridian Green',
    description: 'Cool green that signals calm confidence.',
    swatch: accentPalettes.viridianGreen[500],
  },
  {
    key: 'opal',
    label: 'Opal',
    description: 'Gentle pastel for understated resumes.',
    swatch: accentPalettes.opal[500],
  },
  {
    key: 'darkSeaGreen',
    label: 'Dark Sea Green',
    description: 'Organic green reminiscent of nature.',
    swatch: accentPalettes.darkSeaGreen[500],
  },
  {
    key: 'fernGreen',
    label: 'Fern Green',
    description: 'Earthy green with steady presence.',
    swatch: accentPalettes.fernGreen[500],
  },
  {
    key: 'castletonGreen',
    label: 'Castleton Green',
    description: 'Classic dark green suited for finance and consulting.',
    swatch: accentPalettes.castletonGreen[500],
  },
  {
    key: 'bronze',
    label: 'Bronze',
    description: 'Warm metallic accent for premium presentations.',
    swatch: accentPalettes.bronze[500],
  },
  {
    key: 'kobe',
    label: 'Kobe',
    description: 'Bold russet that stands out in the stack.',
    swatch: accentPalettes.kobe[500],
  },
  {
    key: 'upMaroon',
    label: 'UP Maroon',
    description: 'Deep maroon conveying gravitas and tradition.',
    swatch: accentPalettes.upMaroon[500],
  },
  {
    key: 'downToEarth',
    label: 'Down to Earth',
    description: 'Natural earth tones for grounded professionals.',
    swatch: accentPalettes.downToEarth[500],
  },
  {
    key: 'sophisticatedPinks',
    label: 'Sophisticated Pinks',
    description: 'Confident pink palette ideal for creative roles.',
    swatch: accentPalettes.sophisticatedPinks[500],
  },
  {
    key: 'forestHues',
    label: 'Forest Hues',
    description: 'Rich greens inspired by woodland themes.',
    swatch: accentPalettes.forestHues[500],
  },
  {
    key: 'blueOrange',
    label: 'Blue & Orange',
    description: 'Dynamic contrast for energetic resumes.',
    swatch: accentPalettes.blueOrange[500],
  },
  {
    key: 'navyGold',
    label: 'Navy & Gold',
    description: 'Classic navy paired with a golden accent.',
    swatch: accentPalettes.navyGold[500],
  },
  {
    key: 'redGray',
    label: 'Red & Gray',
    description: 'Bold red tempered by modern gray.',
    swatch: accentPalettes.redGray[500],
  },
  {
    key: 'boldBright',
    label: 'Bold & Bright',
    description: 'High-energy palette for standout resumes.',
    swatch: accentPalettes.boldBright[500],
  },
  {
    key: 'minimalist',
    label: 'Minimalist',
    description: 'Steely teal accent for minimalist layouts.',
    swatch: accentPalettes.minimalist[500],
  },
  {
    key: 'orangeBlue',
    label: 'Orange & Blue',
    description: 'Balanced complementary palette with impact.',
    swatch: accentPalettes.orangeBlue[500],
  },
  {
    key: 'warmNeutral',
    label: 'Warm & Neutral',
    description: 'Soft neutrals with a warm centerpiece.',
    swatch: accentPalettes.warmNeutral[500],
  },
  {
    key: 'royalPurpleBlue',
    label: 'Royal Purple & Blue',
    description: 'Regal blend of purple and indigo hues.',
    swatch: accentPalettes.royalPurpleBlue[500],
  },
  {
    key: 'rosyCharm',
    label: 'Rosy Charm',
    description: 'Delicate pastel blush for approachable resumes.',
    swatch: accentPalettes.rosyCharm[500],
  },
];

export const defaultAccent: AccentKey = 'reference';

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
        borderRadius: 'md',
      },
      defaultProps: {
        colorScheme: 'brand',
        size: 'sm',
      },
    },
    Badge: {
      baseStyle: {
        textTransform: 'none',
        borderRadius: 'full',
        fontWeight: '600',
        letterSpacing: 'wide',
        px: 2.5,
        py: 0.5,
      },
    },
    FormLabel: {
      baseStyle: {
        fontSize: 'xs',
        mb: 1,
      },
    },
    Input: {
      defaultProps: {
        focusBorderColor: 'brand.400',
        size: 'sm',
      },
      sizes: {
        sm: {
          field: {
            borderRadius: 'md',
          },
        },
        md: {
          field: {
            borderRadius: 'md',
          },
        },
      },
    },
    Textarea: {
      defaultProps: {
        focusBorderColor: 'brand.400',
        size: 'sm',
      },
      sizes: {
        sm: {
          borderRadius: 'md',
        },
        md: {
          borderRadius: 'md',
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
          borderRadius: 'xl',
        },
        header: {
          px: 5,
          py: 3,
        },
        body: {
          px: 5,
          py: 4,
        },
        footer: {
          px: 5,
          py: 3,
        },
      },
    },
    Alert: {
      baseStyle: {
        container: {
          borderRadius: 'lg',
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
        lineHeight: 'short',
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

export function getAccentHex(accent: AccentKey, shade: number = 500): string {
  const palette = accentPalettes[accent] ?? accentPalettes[defaultAccent];
  return palette[shade as keyof typeof palette] ?? palette[500];
}
