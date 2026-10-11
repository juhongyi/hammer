"use client";

import { useEffect, useRef, useState } from "react";
import type { Slide } from "@/lib/api";

type Box = { x: number; y: number; width: number; height: number };

function Region({ box, children }: { box: Box; children: React.ReactNode }) {
  return (
    <div
      data-region
      className="slide-region"
      style={{ left: box.x, top: box.y, width: box.width, height: box.height }}
    >
      {children}
    </div>
  );
}

export function SlideCanvas({ slide }: { slide: Slide }) {
  const { content, layout } = slide;
  const count = content.blocks.length;
  const blocks = content.blocks.map((block, position) => ({
    ...block,
    id: `${slide.index}:block:${position}`,
  }));
  const hero = layout.id === "cover" || layout.id === "closing";
  const titleBox = {
    x: 64,
    y: hero ? 76 : 40,
    width: 1152,
    height: hero ? 168 : 96,
  };
  const messageBox = {
    x: 64,
    y: hero ? 264 : 148,
    width: 1152,
    height: hero ? 144 : 124,
  };
  const startY = hero ? 432 : 284;
  const areaHeight = hero ? 224 : 372;
  const columns =
    layout.id === "process"
      ? Math.max(count, 1)
      : layout.id === "list" && count > 4
        ? 3
        : count > 1
          ? 2
          : 1;
  const rows = Math.max(1, Math.ceil(count / columns));
  const gap = 12;
  const width = (1152 - gap * (columns - 1)) / columns;
  const height = (areaHeight - gap * (rows - 1)) / rows;
  const dense = layout.id === "list" && count > 4;
  const compact =
    layout.id === "process" || (layout.id === "list" && count > 2);
  const fontSize = dense ? 14 : compact ? 16 : hero && count > 1 ? 16 : 20;
  const headingSize = dense ? 15 : compact ? 16 : hero && count > 1 ? 20 : 22;
  const headingHeight = dense ? 44 : compact ? 72 : hero ? 64 : 72;
  const padding = compact ? 12 : 16;

  return (
    <div
      className="slide-canvas"
      data-slide-index={slide.index}
      data-layout={layout.id}
    >
      <div
        aria-hidden="true"
        style={{
          position: "absolute",
          left: 64,
          top: hero ? 44 : 22,
          width: 52,
          height: 5,
          borderRadius: 8,
          background: "#087f83",
        }}
      />
      <Region box={titleBox}>
        <h2
          data-text
          className="slide-text slide-title"
          style={{ fontSize: hero ? 48 : 32 }}
        >
          {content.title}
        </h2>
      </Region>
      <Region box={messageBox}>
        <p
          data-text
          className="slide-text slide-message"
          style={{ fontSize: hero ? 30 : 26, color: "#087f83" }}
        >
          {content.key_message}
        </p>
      </Region>
      {blocks.map((block, index) => {
        const x = 64 + (index % columns) * (width + gap);
        const y = startY + Math.floor(index / columns) * (height + gap);
        const step = layout.id === "process" ? 40 : 0;
        const textY = y + padding + step + headingHeight + 6;
        return (
          <div key={block.id}>
            <div
              className="slide-card"
              aria-hidden="true"
              style={{ left: x, top: y, width, height }}
            />
            {step > 0 && (
              <Region
                box={{
                  x: x + padding,
                  y: y + padding,
                  width: width - 2 * padding,
                  height: 32,
                }}
              >
                <p
                  data-text
                  className="slide-text"
                  style={{ color: "#087f83", fontSize: 18, fontWeight: 700 }}
                >
                  {String(index + 1).padStart(2, "0")}
                </p>
              </Region>
            )}
            <Region
              box={{
                x: x + padding,
                y: y + padding + step,
                width: width - 2 * padding,
                height: headingHeight,
              }}
            >
              <h3
                data-text
                className="slide-text slide-heading"
                style={{ fontSize: headingSize }}
              >
                {block.heading}
              </h3>
            </Region>
            <Region
              box={{
                x: x + padding,
                y: textY,
                width: width - 2 * padding,
                height: y + height - padding - textY,
              }}
            >
              <p
                data-text
                className="slide-text slide-body"
                style={{ fontSize }}
              >
                {block.text}
              </p>
            </Region>
          </div>
        );
      })}
      <p className="slide-number">
        SYSTEM ONE{" "}
        <span style={{ marginLeft: 24 }}>
          {String(slide.index + 1).padStart(2, "0")}
        </span>
      </p>
    </div>
  );
}

export function SlidePreview({ slide }: { slide: Slide }) {
  const container = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.5);
  useEffect(() => {
    if (!container.current) return;
    const observer = new ResizeObserver(([entry]) =>
      setScale(Math.min(entry.contentRect.width / 1280, 1)),
    );
    observer.observe(container.current);
    return () => observer.disconnect();
  }, []);
  return (
    <div
      ref={container}
      className="w-full overflow-hidden rounded-xl border border-border bg-white"
      style={{ height: 720 * scale }}
    >
      <div
        style={{ transform: `scale(${scale})`, transformOrigin: "top left" }}
      >
        <SlideCanvas slide={slide} />
      </div>
    </div>
  );
}
