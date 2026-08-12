const videoId = "S9l3YWjk1VA";
const videoUrl = `https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1&mute=1&controls=0&loop=1&playlist=${videoId}&playsinline=1&rel=0&iv_load_policy=3&disablekb=1&fs=0`;

export function BackgroundReel() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 overflow-hidden bg-black"
    >
      <iframe
        allow="autoplay; encrypted-media"
        className="absolute left-1/2 top-1/2 border-0"
        loading="eager"
        referrerPolicy="strict-origin-when-cross-origin"
        src={videoUrl}
        style={{
          width: "max(100vw, 177.78vh)",
          height: "max(100vh, 56.25vw)",
          transform: "translate(-50%, -50%)",
        }}
        tabIndex={-1}
        title="Vídeo de fundo da LinkAI"
      />
    </div>
  );
}
