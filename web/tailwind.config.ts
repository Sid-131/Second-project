import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
        "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
        "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                // Material 3 dynamically generated mapping based on Groww (#00d09c) primary seed
                md: {
                    primary: '#006c4f',
                    onPrimary: '#ffffff',
                    primaryContainer: '#6cf9ca',
                    onPrimaryContainer: '#002116',
                    secondary: '#4b6358',
                    onSecondary: '#ffffff',
                    secondaryContainer: '#cde9db',
                    onSecondaryContainer: '#082017',
                    tertiary: '#3f6374',
                    onTertiary: '#ffffff',
                    tertiaryContainer: '#c4e8fd',
                    onTertiaryContainer: '#001f2a',
                    error: '#ba1a1a',
                    onError: '#ffffff',
                    errorContainer: '#ffdad6',
                    onErrorContainer: '#410002',
                    background: '#fbfdfc',
                    onBackground: '#191c1b',
                    surface: '#fbfdfc',
                    onSurface: '#191c1b',
                    surfaceVariant: '#dbe5de',
                    onSurfaceVariant: '#404944',
                    outline: '#707973',
                    outlineVariant: '#bfc9c2',
                    surfaceContainer: '#eff1ee',
                    surfaceContainerHigh: '#e9ece9',
                    surfaceContainerHighest: '#e3e6e3',
                },
                groww: {
                    DEFAULT: "#00d09c",
                    dark: "#00b88a",
                    light: "#e5faf4",
                },
                text: {
                    main: "#44475b",
                    light: "#7b7e8c"
                },
                bg: {
                    main: "#f4f5f9",
                    card: "#ffffff",
                    border: "#ecedf0"
                }
            },
            borderRadius: {
                'md-sm': '8px',
                'md': '12px',
                'md-lg': '16px',
                'md-xl': '24px',
                'md-2xl': '28px', // standard M3 large component radius
            }
        },
    },
    plugins: [
        require("@tailwindcss/typography"),
    ],
};
export default config;
