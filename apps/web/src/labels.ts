export const L: Record<string, string> = {
  WORKER: '근로자', COMPANY_MANAGER: '기업 담당자', VDREAM_MANAGER: '브이드림 매니저', SYSTEM_ADMIN: '시스템관리자',
  PENDING: '대기', ACTIVE: '재직중', RESIGNED: '퇴사',
  DRAFT: '작성중', PENDING_APPROVAL: '승인 대기', REJECTED: '반려', PUBLISHED: '게시중', CLOSED: '마감',
  APPLIED: '지원 완료', DOCUMENT_PASSED: '서류 합격', DOCUMENT_FAILED: '서류 불합격', INTERVIEW_SCHEDULED: '면접 예정',
  PASSED: '최종 합격', FAILED: '불합격', HIRED: '입사', CANCELLED: '취소',
  ASSIGNED: '배정됨', IN_PROGRESS: '진행중', COMPLETED: '완료',
  SUBMITTED: '제출됨', CONFIRMED: '확인됨', RETURNED: '보완 요청',
  NORMAL: '정상', LATE: '지각', EARLY_LEAVE: '조퇴', LATE_EARLY_LEAVE: '지각·조퇴', ABSENT: '결근', ON_LEAVE: '휴가',
  APPROVED: '승인', WITHDRAWN: '철회',
  ANNUAL: '연차', HALF_DAY_AM: '오전 반차', HALF_DAY_PM: '오후 반차', SICK: '병가', OTHER: '기타',
  LOW: '낮음', HIGH: '높음',
  REMOTE: '재택', HYBRID: '혼합', MONTHLY: '월급', HOURLY: '시급', FIXED_TERM: '기간제', INDEFINITE: '기간의 정함 없음',
  SEVERE: '중증', MILD: '경증', SEEKING: '구직중', NOT_SEEKING: '구직 안 함',
  VIDEO: '화상', VISIT: '방문', PHONE: '전화', CHAT: '메신저',
  DOUBLE: '인정(2배수)', SINGLE: '인정(1배수)', EXCLUDED: '제외 가능', NEEDS_REVIEW: '확인 필요',
  ALL: '모두', VDREAM: '브이드림 매니저', COMPANY: '기업', MALE: '남', FEMALE: '여',
  DATA_LABELING: '데이터 라벨링', DOCUMENT_ENTRY: '문서·데이터 입력', CONTENT_MONITORING: '콘텐츠 모니터링', DESIGN: '디자인',
  VIDEO_EDITING: '영상 편집', CONTENT_WRITING: '콘텐츠 작성', CUSTOMER_SUPPORT: '고객 응대', RESEARCH: '리서치·조사',
  PHYSICAL: '지체', BRAIN_LESION: '뇌병변', VISUAL: '시각', HEARING: '청각', SPEECH: '언어', FACIAL: '안면', KIDNEY: '신장', HEART: '심장',
  LIVER: '간', RESPIRATORY: '호흡기', OSTOMY: '장루·요루', EPILEPSY: '뇌전증', INTELLECTUAL: '지적', AUTISM: '자폐성', MENTAL: '정신',
  ELEMENTARY: '초등학교', MIDDLE: '중학교', UNIVERSITY: '대학교', GRADUATE: '대학원', VOCATIONAL: '직업교육',
  ENROLLED: '재학중', GRADUATED: '졸업', DROPPED_OUT: '중퇴', INTERN: '인턴', TRAINEE: '실습', EMPLOYEE: '직원',
}
export const lb = (k?: string | null) => (k ? L[k] ?? k : '-')
export const tone = (k?: string | null): 'success' | 'warning' | 'error' | 'info' | 'default' => {
  if (!k) return 'default'
  if (['CONFIRMED', 'COMPLETED', 'APPROVED', 'NORMAL', 'PUBLISHED', 'HIRED', 'PASSED', 'ACTIVE', 'DOUBLE', 'SINGLE', 'SEEKING'].includes(k)) return 'success'
  if (['SUBMITTED', 'PENDING', 'PENDING_APPROVAL', 'RETURNED', 'LATE', 'EARLY_LEAVE', 'LATE_EARLY_LEAVE', 'NEEDS_REVIEW', 'INTERVIEW_SCHEDULED', 'DOCUMENT_PASSED', 'APPLIED'].includes(k)) return 'warning'
  if (['ABSENT', 'REJECTED', 'FAILED', 'DOCUMENT_FAILED', 'CANCELLED', 'EXCLUDED', 'RESIGNED'].includes(k)) return 'error'
  if (['IN_PROGRESS', 'ON_LEAVE', 'ASSIGNED'].includes(k)) return 'info'
  return 'default'
}
export const kst = (iso?: string | null, withDate = true) => {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleString('ko-KR', { timeZone: 'Asia/Seoul', ...(withDate ? { month: 'numeric', day: 'numeric' } : {}), hour: '2-digit', minute: '2-digit', hour12: false })
}
export const ymd = (d = new Date()) => d.toLocaleDateString('sv-SE', { timeZone: 'Asia/Seoul' })
export const ym = (d = new Date()) => ymd(d).slice(0, 7)
export const hm = (min: number) => `${Math.floor(min / 60)}시간${min % 60 ? ` ${min % 60}분` : ''}`
export const WEEK = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
export const WEEK_KO: Record<string, string> = { MON: '월', TUE: '화', WED: '수', THU: '목', FRI: '금', SAT: '토', SUN: '일' }
