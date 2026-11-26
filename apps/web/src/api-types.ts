/** OpenAPI에서 생성한 스키마 타입 (scripts/generate-types.sh). 요청 본문과 열거형의 원천은 백엔드 Python 코드다. */
import type { components } from './api-schema'

type S = components['schemas']
export type TaskIn = S['TaskIn']
export type MsgIn = S['MsgIn']
export type LeaveIn = S['LeaveIn']
export type UserRole = S['UserRole']
export type TaskStatus = S['TaskStatus']
export type WorkLogStatus = S['WorkLogStatus']
export type MessageAudience = S['MessageAudience']
