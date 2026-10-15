from html import escape
import os
from pathlib import Path

from playwright.async_api import async_playwright

from .models import TextError


STYLE = """
@font-face { font-family: Presentation; src: url('/api/font') format('truetype'); font-display: block; }
* { box-sizing: border-box; }
html, body { margin: 0; width: 1280px; height: 720px; background: #f8fafc; }
body { font-family: Presentation, 'Apple SD Gothic Neo', sans-serif; color: #10243b; }
.slide { width: 1280px; height: 720px; position: relative; overflow: hidden; border-top: 10px solid #166d94; }
.slot { position: absolute; overflow: hidden; overflow-wrap: anywhere; white-space: pre-wrap; }
.title { left: 64px; top: 50px; width: 1152px; height: 100px; font-size: 38px; font-weight: 700; line-height: 1.25; }
.message { left: 64px; top: 172px; width: 1152px; height: 116px; font-size: 26px; line-height: 1.4; color: #166d94; }
.items { left: 64px; top: 320px; width: 1152px; height: 328px; display: grid; gap: 16px; }
.item { min-height: 0; min-width: 0; overflow: hidden; padding: 14px 18px; background: #e8f0f5; border-radius: 8px; display: flex; flex-direction: column; gap: 6px; }
.item-title { flex: 0 0 auto; font-weight: 700; font-size: 21px; line-height: 1.3; }
.item-description { min-height: 0; font-size: 18px; line-height: 1.4; overflow: hidden; }
.layout-cover .title { top: 215px; height: 260px; font-size: 64px; line-height: 1.4; }
.layout-closing { border-top-color: #4c6b4b; }
.footer { position: absolute; bottom: 16px; right: 64px; font-size: 16px; color: #54718b; }
"""


def font_path() -> Path:
    return Path(os.getenv("FONT_PATH", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"))


def slide_html(slide: dict, index: int = 1) -> str:
    layout_id = slide["layout"]["id"]
    copy = slide["copy"]
    content = f'<div class="slot title" data-slot="title">{escape(copy["title"])}</div>'
    if "message" in copy:
        content += f'<div class="slot message" data-slot="message">{escape(copy["message"])}</div>'
    items = copy.get("items", [])
    if items:
        columns = 1 if layout_id == "message" else 3 if layout_id == "process" else 2
        rows = (len(items) + columns - 1) // columns
        content += (f'<div class="slot items" data-slot="items" style="grid-template-columns:repeat({columns},1fr);'
                    f'grid-template-rows:repeat({rows},1fr)">')
        for item in items:
            content += ('<div class="item"><div class="item-title" data-text>' + escape(item["title"]) +
                        '</div><div class="item-description" data-text>' + escape(item["description"]) + '</div></div>')
        content += '</div>'
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{escape(copy["title"])}</title>'
            f'<style>{STYLE}</style></head><body><main class="slide layout-{layout_id}">{content}'
            f'<div class="footer">{index:02}</div></main></body></html>')


CHECK_SCRIPT = """() => {
    const errors = [];
    const slide = document.querySelector('.slide').getBoundingClientRect();
    const slots = [...document.querySelectorAll('[data-slot]')];
    const contains = (a, b) => b.left >= a.left - 1 && b.top >= a.top - 1 && b.right <= a.right + 1 && b.bottom <= a.bottom + 1;
    for (const element of [...slots, ...document.querySelectorAll('[data-text], .item')]) {
        if (element.scrollHeight > element.clientHeight + 1 || element.scrollWidth > element.clientWidth + 1)
            errors.push((element.dataset.slot || element.className) + ': 텍스트 잘림');
        if (!contains(slide, element.getBoundingClientRect())) errors.push('슬라이드 영역 이탈');
        if (element.closest('.item') && !contains(element.closest('.item').getBoundingClientRect(), element.getBoundingClientRect()))
            errors.push('항목 영역 이탈');
    }
    for (let i = 0; i < slots.length; i++) for (let j = i + 1; j < slots.length; j++) {
        const a = slots[i].getBoundingClientRect(), b = slots[j].getBoundingClientRect();
        if (Math.min(a.right, b.right) - Math.max(a.left, b.left) > 1 &&
            Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1) errors.push('슬롯 겹침');
    }
    return [...new Set(errors)];
}"""


class Renderer:
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        try:
            self.browser = await self.playwright.chromium.launch()
            self.page = await self.browser.new_page(viewport={"width": 1280, "height": 720})
            async def assets(route):
                if route.request.url.endswith("/api/font"):
                    if font_path().is_file():
                        await route.fulfill(path=str(font_path()), content_type="font/ttf")
                    else:
                        await route.abort()
                else:
                    await route.fulfill(content_type="text/html", body="<!doctype html><html></html>")
            await self.page.route("http://renderer.local/**", assets)
            await self.page.goto("http://renderer.local/")
        except Exception:
            await self.playwright.stop()
            raise
        return self

    async def __aexit__(self, *_):
        await self.browser.close()
        await self.playwright.stop()

    async def check(self, slide: dict) -> None:
        await self.page.set_content(slide_html(slide))
        await self.page.evaluate("document.fonts.ready")
        if font_path().is_file() and not await self.page.evaluate("document.fonts.check('18px Presentation')"):
            raise RuntimeError("슬라이드 검사 폰트를 불러오지 못했습니다.")
        errors = await self.page.evaluate(CHECK_SCRIPT)
        if errors:
            raise TextError("실제 배치 검사 실패: " + ", ".join(errors) + ". 문구를 더 짧게 작성하세요.")
