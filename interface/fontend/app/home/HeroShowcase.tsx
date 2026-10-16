"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { BrandLogo } from "@/components/BrandLogo";
import { ArrowRight } from "lucide-react";

const slides = [
  {
    tag: "01 / THU THẬP",
    title: "Mọi loại thuốc.",
    accent: "Một danh sách.",
    description: "Gom thuốc kê đơn, vitamin và thực phẩm vào cùng một nơi.",
    name: "Thu thập",
    theme: "collect",
  },
  {
    tag: "02 / ĐỐI CHIẾU",
    title: "Kết nối thông tin.",
    accent: "Hiểu rõ tương tác.",
    description:
      "Đối chiếu các thành phần để nhận biết những tương tác cần lưu ý.",
    name: "Phân tích",
    theme: "analyse",
  },
  {
    tag: "03 / TRAO ĐỔI",
    title: "Hiểu điều cần hỏi.",
    accent: "Chủ động hơn.",
    description:
      "Chuẩn bị câu hỏi rõ ràng để trao đổi cùng bác sĩ hoặc dược sĩ.",
    name: "Trao đổi",
    theme: "discuss",
  },
];

export function HeroShowcase({ onStart }: { onStart: () => void }) {
  const [active, setActive] = useState(0);
  const [direction, setDirection] = useState(1);
  const slide = slides[active];

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDirection(1);
      setActive((value) => (value + 1) % slides.length);
    }, 3000);
    return () => window.clearTimeout(timer);
  }, [active]);

  function goTo(index: number, nextDirection: number) {
    setDirection(nextDirection);
    setActive((index + slides.length) % slides.length);
  }

  return (
    <div
      className={`hero-showcase hero-showcase--${slide.theme}`}
      role="region"
      aria-roledescription="trình chiếu"
      aria-label="Khám phá MediCheck"
    >
      <div className="hero-showcase-halo" aria-hidden="true" />
      <div className="hero-showcase-shell">
        <div aria-live="off" aria-atomic="true">
          <div
            key={active}
            className={`hero-showcase-slide ${direction < 0 ? "is-backward" : ""}`}
            role="group"
            aria-roledescription="slide"
            aria-label={`${active + 1} / 3: ${slide.name}`}
          >
            <div className="hero-showcase-art hero-showcase-art--image">
              <Image
                src={`/home-slides/${slide.theme}-v1.png`}
                alt={
                  [
                    "Minh họa khay thuốc, lọ vitamin và danh sách thuốc trên nền xanh ngọc",
                    "Minh họa kính lúp đối chiếu thuốc và thành phần thực vật trên nền xanh lam",
                    "Minh họa người dùng trao đổi danh sách thuốc với bác sĩ trên nền tím nhạt",
                  ][active]
                }
                width={1672}
                height={941}
                sizes="(max-width: 640px) 90vw, 540px"
                priority={active === 0}
                className="hero-showcase-image"
              />
              <span className="hero-showcase-image-count">
                0{active + 1} / 03
              </span>
              <span className="hero-showcase-image-label">
                <BrandLogo size={18} className="bg-white" />
                {slide.tag}
              </span>
            </div>
            <div className="hero-showcase-copy">
              <div className="hero-showcase-heading-row">
                <h2>
                  {slide.title}
                  <br />
                  <span>{slide.accent}</span>
                </h2>
                <button className="hero-showcase-cta" onClick={onStart}>
                  Bắt đầu kiểm tra <ArrowRight size={16} />
                </button>
              </div>
              <p className="hero-showcase-description">{slide.description}</p>
            </div>
          </div>
        </div>
        <div className="hero-showcase-dots" aria-label="Chọn slide">
          {slides.map((item, index) => (
            <button
              key={item.name}
              className="hero-showcase-dot"
              onClick={() => goTo(index, index > active ? 1 : -1)}
              aria-label={`Bước ${index + 1}: ${item.name}`}
              aria-current={active === index ? "step" : undefined}
            >
              <span aria-hidden="true" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
