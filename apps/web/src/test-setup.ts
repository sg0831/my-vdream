// jsdom에는 matchMedia가 없다. 테스트마다 폭을 바꿀 수 있게 전역 변수로 흉내 낸다.
;(globalThis as any).__viewportWidth = 1280
window.matchMedia = ((q: string) => {
  const m = /min-width:\s*(\d+)px/.exec(q)
  const matches = m ? (globalThis as any).__viewportWidth >= Number(m[1]) : false
  return { matches, media: q, onchange: null, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {}, dispatchEvent: () => false }
}) as any
