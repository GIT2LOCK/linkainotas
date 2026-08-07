import { useEffect, useState } from "react";
import take1 from "@/assets/take1.mp4.asset.json";
import take2 from "@/assets/take2.mp4.asset.json";
import take3 from "@/assets/take3.mp4.asset.json";

const takes = [take1.url, take2.url, take3.url];
const TAKE_MS = 7000;


export function BackgroundReel() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const id = window.setInterval(
      () => setActive((i) => (i + 1) % takes.length),
      TAKE_MS,
    );
    return () => window.clearInterval(id);
  }, []);

  return (
    <div aria-hidden="true" className="absolute inset-0 overflow-hidden">
      {takes.map((src, i) => (
        <video
          key={src}
          src={src}
          autoPlay
          muted
          loop
          playsInline
          preload="auto"
          className="absolute inset-0 h-full w-full object-cover transition-opacity duration-[1400ms] ease-in-out"
          style={{
            opacity: i === active ? 1 : 0,
            animation: `reel-zoom ${TAKE_MS * 2}ms ease-in-out infinite alternate`,
            animationDelay: `${i * -900}ms`,
          }}
        />
      ))}
    </div>
  );
}