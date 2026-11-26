import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'

afterEach(cleanup)
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { hm, lb, tone } from './labels'
import { AuthProvider } from './auth'
import { PhoneFrame, StatusChip } from './ui'

function wrap(ui: React.ReactNode) {
  return render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><AuthProvider>{ui}</AuthProvider></MemoryRouter></QueryClientProvider>)
}

describe('labels', () => {
  it('상태 코드를 한국어로 바꾸고 톤을 고른다', () => {
    expect(lb('RETURNED')).toBe('보완 요청')
    expect(lb('DOUBLE')).toBe('인정(2배수)')
    expect(tone('CONFIRMED')).toBe('success')
    expect(tone('ABSENT')).toBe('error')
    expect(hm(135)).toBe('2시간 15분')
  })
})

describe('StatusChip', () => {
  it('색상만이 아니라 텍스트 레이블로 상태를 보여준다 (ACCS-007)', () => {
    wrap(<StatusChip value="SUBMITTED" />)
    expect(screen.getByText('제출됨')).toBeTruthy()
  })
})

describe('PhoneFrame', () => {
  it('데스크톱 폭에서는 휴대폰 프레임과 안내를 보여준다', () => {
    ;(globalThis as any).__viewportWidth = 1280
    wrap(<PhoneFrame><p>근로자 화면</p></PhoneFrame>)
    expect(screen.getByText('새 창으로 열기')).toBeTruthy()
    expect(screen.getByText('이 화면에서 해볼 것')).toBeTruthy()
  })
  it('휴대폰 폭에서는 프레임 없이 화면을 가득 채운다', () => {
    ;(globalThis as any).__viewportWidth = 390
    wrap(<PhoneFrame><p>근로자 화면</p></PhoneFrame>)
    expect(screen.getByText('근로자 화면')).toBeTruthy()
    expect(screen.queryByText('새 창으로 열기')).toBeNull()
  })
})
