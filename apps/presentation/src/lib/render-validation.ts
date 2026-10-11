import type { Presentation } from "./api";

export async function inspectSlides(
  root: HTMLElement,
  presentation: Presentation,
) {
  const text = presentation.slides
    .map((slide) => JSON.stringify(slide.content))
    .join(" ");
  let fontLoaded = false;
  try {
    const fonts = await Promise.all(
      [400, 500, 700].map((weight) =>
        document.fonts.load(`${weight} 24px "Noto Sans KR"`, text),
      ),
    );
    await document.fonts.ready;
    fontLoaded = fonts.every(
      (faces) =>
        faces.length > 0 && faces.every((face) => face.status === "loaded"),
    );
  } catch {
    fontLoaded = false;
  }
  await new Promise<void>((resolve) =>
    requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
  );
  const canvases = Array.from(
    root.querySelectorAll<HTMLElement>("[data-slide-index]"),
  );
  return {
    run_id: presentation.run_id ?? "",
    font_loaded: fontLoaded,
    pages: canvases.map((canvas) => {
      const issues: string[] = [];
      const bounds = canvas.getBoundingClientRect();
      const regions = Array.from(
        canvas.querySelectorAll<HTMLElement>("[data-region]"),
      );
      const rectangles = regions.map((region) =>
        region.getBoundingClientRect(),
      );
      regions.forEach((region, index) => {
        const box = rectangles[index];
        const content = region
          .querySelector<HTMLElement>("[data-text]")
          ?.getBoundingClientRect();
        if (
          region.clientHeight <= 0 ||
          region.scrollHeight > region.clientHeight + 1 ||
          region.scrollWidth > region.clientWidth + 1 ||
          (content &&
            (content.bottom > box.bottom + 1 || content.right > box.right + 1))
        )
          issues.push(`슬롯 ${index + 1}의 내용이 잘립니다.`);
        if (
          box.left < bounds.left - 1 ||
          box.top < bounds.top - 1 ||
          box.right > bounds.right + 1 ||
          box.bottom > bounds.bottom + 1
        )
          issues.push(`슬롯 ${index + 1}이 슬라이드 밖으로 나갑니다.`);
        rectangles.slice(index + 1).forEach((other) => {
          if (
            Math.min(box.right, other.right) - Math.max(box.left, other.left) >
              1 &&
            Math.min(box.bottom, other.bottom) - Math.max(box.top, other.top) >
              1
          )
            issues.push(`슬롯 ${index + 1}이 다른 슬롯과 겹칩니다.`);
        });
      });
      return {
        index: Number(canvas.dataset.slideIndex),
        issues: [...new Set(issues)],
      };
    }),
  };
}
