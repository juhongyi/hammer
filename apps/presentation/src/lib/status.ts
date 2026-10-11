import type { Presentation } from "./api";

export function statusLabel(status: Presentation["status"]) {
  return {
    outline_ready: "개요 편집",
    queued: "생성 대기",
    generating: "생성 중",
    awaiting_validation: "배치 검사 중",
    completed: "완료",
    failed: "실패",
  }[status];
}
