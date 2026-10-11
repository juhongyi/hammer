import { z } from "zod";

export const expressionIds = ["introduction", "emphasis", "enumeration", "comparison", "process", "closing"] as const;
export const capacities = {
  cover: [0, 1, 120], message: [0, 2, 160], list: [2, 6, 100], comparison: [2, 2, 180], process: [3, 5, 80], closing: [0, 2, 120],
} as const;
const required = z.string().trim().min(1, "필수 항목입니다.");
const textSlot = z.object({ role: z.enum(["title", "key_message"]), content_kind: z.literal("text").default("text"), description: required, max_chars: z.number().int().min(1) });

export const catalogueSchema = z.object({
  version: z.number().int().min(1),
  types: z.array(z.object({ id: z.enum(expressionIds), name: required, description: required })).length(6),
  layouts: z.array(z.object({
    id: z.enum(["cover", "message", "list", "comparison", "process", "closing"]),
    name: required, purpose: required, enabled: z.boolean(), supports: z.array(z.enum(expressionIds)).min(1, "지원 유형을 하나 이상 선택하세요."),
    slots: z.object({ title: textSlot, key_message: textSlot, body: z.object({
      role: z.literal("body").default("body"), content_kind: z.literal("heading_text_blocks").default("heading_text_blocks"), description: required,
      min_items: z.number().int().min(0), max_items: z.number().int().min(0), heading_max_chars: z.number().int().min(1).max(32), text_max_chars: z.number().int().min(1),
    }) }),
  }).superRefine((layout, ctx) => {
    const [minimum, maximum, textMax] = capacities[layout.id];
    const body = layout.slots.body;
    const issue = (path: (string | number)[], message: string) => ctx.addIssue({ code: "custom", path, message });
    if (body.min_items < minimum || body.min_items > body.max_items) issue(["slots", "body", "min_items"], `블록 최소 수는 ${minimum} 이상이며 최대 수 이하이어야 합니다.`);
    if (body.max_items > maximum) issue(["slots", "body", "max_items"], `블록 최대 수는 ${maximum} 이하이어야 합니다.`);
    if (body.text_max_chars > textMax) issue(["slots", "body", "text_max_chars"], `본문은 ${textMax}자 이하이어야 합니다.`);
    if (layout.slots.title.max_chars > 48) issue(["slots", "title", "max_chars"], "제목은 48자 이하이어야 합니다.");
    if (layout.slots.key_message.max_chars > 96) issue(["slots", "key_message", "max_chars"], "핵심 메시지는 96자 이하이어야 합니다.");
  })).length(6),
});
