import { createTheme, type PaletteMode, type Theme } from '@mui/material/styles'

/** 브이드림 사이트에서 수집한 브랜드 토큰 (기술스펙 6.2.1) */
export const tokens = {
  mint: { 50: '#D7F4F2', 300: '#72C9C1', 400: '#5DBEB6', 500: '#2EB6AA', 700: '#0B7A71', 800: '#0E877D', gradientStart: '#23CDB7' },
  violet: { 50: '#D6D1F0', 200: '#9C93D1', 300: '#8377C2', 500: '#584C9D', 700: '#433594' },
  navy: { 800: '#1E1638', 900: '#150F29', 950: '#0C0918' },
  gray: { 5: '#F9FAFB', 20: '#E5E7EB', 40: '#9CA3AF', 60: '#4B5563', 70: '#374151', 90: '#111827' },
  status: {
    error: { bg: '#FAEBE9', text: '#90241B', main: '#CE3426' },
    success: { bg: '#EBF7F2', text: '#267D58', main: '#36B37E' },
    warning: { bg: '#FFF7E6', text: '#805600', main: '#FFAB00' },
    info: { bg: '#E6F2FB', text: '#085691', main: '#0B78CB' },
  },
}

export type Area = 'worker' | 'admin'

export function makeTheme(area: Area, mode: PaletteMode): Theme {
  const dark = mode === 'dark'
  const t = tokens
  const primary = area === 'worker'
    ? (dark ? { main: t.mint[500], contrastText: t.navy[950] } : { main: t.mint[700], light: t.mint[500], dark: t.mint[800], contrastText: '#FFFFFF' })
    : (dark ? { main: t.violet[200], contrastText: t.navy[950] } : { main: t.violet[500], dark: t.violet[700], contrastText: '#FFFFFF' })
  const secondary = area === 'worker'
    ? (dark ? { main: t.violet[200], contrastText: t.navy[950] } : { main: t.violet[500], contrastText: '#FFFFFF' })
    : (dark ? { main: t.mint[500], contrastText: t.navy[950] } : { main: t.mint[700], contrastText: '#FFFFFF' })
  const base = area === 'worker' ? 18 : 16
  return createTheme({
    palette: {
      mode, primary, secondary,
      background: dark ? { default: t.navy[950], paper: t.navy[900] } : { default: '#FFFFFF', paper: '#F6F5FB' },
      text: dark ? { primary: t.gray[5], secondary: t.gray[40] } : { primary: t.gray[90], secondary: t.gray[60] },
      divider: dark ? t.gray[70] : t.gray[20],
      error: { main: t.status.error.main }, success: { main: t.status.success.main },
      warning: { main: t.status.warning.main }, info: { main: t.status.info.main },
    },
    shape: { borderRadius: 12 },
    typography: {
      fontFamily: '"Pretendard Variable", Pretendard, -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif',
      fontSize: base - 2, body1: { fontSize: base }, body2: { fontSize: base - 2 },
      h1: { fontSize: 26, fontWeight: 800 }, h2: { fontSize: 22, fontWeight: 700 }, h3: { fontSize: 19, fontWeight: 700 },
      button: { fontWeight: 700, textTransform: 'none' },
    },
    components: {
      MuiButton: { styleOverrides: { root: { minHeight: area === 'worker' ? 44 : 36 } } },
      MuiButtonBase: { styleOverrides: { root: { '&.Mui-focusVisible': { outline: `2px solid ${dark ? t.mint[300] : t.violet[500]}`, outlineOffset: 2 } } } },
      MuiPaper: { styleOverrides: { root: { backgroundImage: 'none' } } },
      MuiTableCell: { styleOverrides: { root: { fontSize: area === 'worker' ? 16 : 15 } } },
    },
  })
}
