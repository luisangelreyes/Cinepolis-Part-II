import { useEffect, useCallback, useState } from "react";
import { usePelicula } from "../hooks/usePelicula";

/* ── Datos de relleno para actores/director ──────────────────────── */
const ACTORES_FALLBACK = [
  { nombre: "Tom Holland", foto: "https://i.pravatar.cc/48?img=11" },
  { nombre: "Anne Hathaway", foto: "https://i.pravatar.cc/48?img=47" },
  { nombre: "Matthew Damon", foto: "https://i.pravatar.cc/48?img=32" },
  { nombre: "Robert Pattinson", foto: "https://i.pravatar.cc/48?img=54" },
];
const DIRECTOR_FALLBACK = { nombre: "Christopher Nolan", foto: "https://i.pravatar.cc/48?img=3" };

/* ── Helper: convierte URL de YouTube a embed ────────────────────── */
function toEmbedUrl(url: string | null) {
  if (!url) return null;
  const ytMatch = url.match(/(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|shorts\/))([^&?/]+)/);
  if (ytMatch) return `https://www.youtube.com/embed/${ytMatch[1]}?autoplay=1&rel=0`;
  return url;
}

interface Props {
  peliculaId: number | null;
  onClose: () => void;
}

export function SinopsisModal({ peliculaId, onClose }: Props) {
  const { data: pelicula, isLoading } = usePelicula(peliculaId);
  const [trailerAbierto, setTrailerAbierto] = useState(false);

  /* Cerrar con Escape — si hay trailer abierto, cierra solo el trailer */
  const handleKey = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (trailerAbierto) setTrailerAbierto(false);
        else onClose();
      }
    },
    [onClose, trailerAbierto]
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.body.style.overflow = "";
    };
  }, [handleKey]);

  const embedUrl = toEmbedUrl(pelicula?.trailer_url ?? null);

  return (
    <>
      {/* ════════ OVERLAY PRINCIPAL — SINOPSIS ════════ */}
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        style={{ backgroundColor: "rgba(0,0,0,0.88)" }}
        onClick={onClose}
      >
        <div
          className="relative w-full max-w-5xl rounded-2xl overflow-hidden shadow-2xl"
          style={{
            backgroundColor: "#0f0f12",
            border: "1px solid #2a2a35",
            maxHeight: "92vh",
            overflowY: "auto",
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Botón Cerrar */}
          <button
            id="btn-cerrar-sinopsis"
            onClick={onClose}
            className="absolute top-4 right-4 z-10 flex items-center gap-1.5 text-xs font-semibold text-white bg-black/60 hover:bg-black/90 rounded px-3 py-1.5 transition-colors"
          >
            Cerrar ✕
          </button>

          {isLoading || !pelicula ? (
            <div className="flex items-center justify-center h-80">
              <div className="w-10 h-10 border-4 border-cine-gold border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <>
              {/* Hero con banner */}
              <div className="relative h-64 sm:h-72 overflow-hidden shrink-0">
                {pelicula.banner_url ? (
                  <img
                    src={pelicula.banner_url}
                    alt=""
                    className="w-full h-full object-cover"
                    style={{ filter: "brightness(0.45)" }}
                  />
                ) : (
                  <div
                    className="w-full h-full"
                    style={{ background: "linear-gradient(135deg, #1a1a2e, #16213e)" }}
                  />
                )}
                {/* Gradiente inferior */}
                <div
                  className="absolute inset-x-0 bottom-0 h-32"
                  style={{ background: "linear-gradient(to top, #0f0f12, transparent)" }}
                />
              </div>

              {/* Cuerpo: poster + info */}
              <div
                className="flex flex-col sm:flex-row gap-6 px-6 pb-8"
                style={{ marginTop: "-100px", position: "relative", zIndex: 1 }}
              >
                {/* Póster */}
                <div className="shrink-0 w-32 sm:w-44 rounded-xl overflow-hidden shadow-2xl border border-white/10 mx-auto sm:mx-0">
                  {pelicula.poster_url ? (
                    <img
                      src={pelicula.poster_url}
                      alt={`Póster de ${pelicula.titulo}`}
                      className="w-full h-auto object-cover"
                    />
                  ) : (
                    <div className="aspect-[2/3] bg-cine-bg-raised flex items-center justify-center text-cine-slate text-xs">
                      Sin imagen
                    </div>
                  )}
                </div>

                {/* Info derecha */}
                <div className="flex-1 pt-28 sm:pt-24 min-w-0">
                  <h2 className="font-display text-3xl sm:text-4xl text-white leading-tight">
                    {pelicula.titulo}
                  </h2>

                  <p className="text-cine-slate text-sm mt-2">
                    {pelicula.duracion_min} min
                    {pelicula.genero ? (
                      <> · <span className="uppercase">{pelicula.genero}</span></>
                    ) : null}
                  </p>

                  {/* Botón Tráiler */}
                  {embedUrl && (
                    <div className="flex flex-wrap gap-3 mt-5">
                      <button
                        id="btn-ver-trailer"
                        onClick={() => setTrailerAbierto(true)}
                        className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold text-white transition-all hover:scale-105 active:scale-95"
                        style={{ backgroundColor: "#1a1a2e", border: "1px solid #444" }}
                      >
                        <svg
                          className="w-5 h-5 text-cine-gold fill-current"
                          viewBox="0 0 24 24"
                        >
                          <path d="M8 5v14l11-7z" />
                        </svg>
                        Ver tráiler
                      </button>
                    </div>
                  )}

                  {/* Sinopsis */}
                  <div className="mt-6">
                    <p className="text-xs font-bold text-cine-gold uppercase tracking-wider mb-2">
                      Sinopsis
                    </p>
                    <p className="text-sm leading-relaxed" style={{ color: "#bdbdce" }}>
                      {pelicula.sinopsis || "Sinopsis no disponible."}
                    </p>
                  </div>

                  {/* Clasificación + Géneros */}
                  <div className="flex flex-wrap gap-6 mt-6">
                    <div>
                      <p className="text-[10px] font-bold text-cine-slate uppercase tracking-wider mb-1">
                        Clasificación
                      </p>
                      <span className="text-2xl font-display font-bold text-cine-cream">
                        {pelicula.clasificacion}
                      </span>
                    </div>
                    {pelicula.genero && (
                      <div>
                        <p className="text-[10px] font-bold text-cine-slate uppercase tracking-wider mb-1">
                          Género
                        </p>
                        <p className="text-sm font-bold text-cine-cream uppercase">
                          {pelicula.genero}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Sección: Director + Actores */}
              <div
                className="grid sm:grid-cols-2 gap-8 px-6 pb-8 pt-4"
                style={{ borderTop: "1px solid #2a2a35" }}
              >
                <div>
                  <p className="text-[10px] font-bold text-cine-gold uppercase tracking-wider mb-3">
                    Dirección
                  </p>
                  <div className="flex items-center gap-3">
                    <img
                      src={DIRECTOR_FALLBACK.foto}
                      alt={DIRECTOR_FALLBACK.nombre}
                      className="w-10 h-10 rounded-full object-cover border border-cine-line"
                    />
                    <span className="text-sm text-cine-cream">{DIRECTOR_FALLBACK.nombre}</span>
                  </div>
                </div>

                <div>
                  <p className="text-[10px] font-bold text-cine-gold uppercase tracking-wider mb-3">
                    Actores
                  </p>
                  <div className="space-y-2">
                    {ACTORES_FALLBACK.map((a) => (
                      <div key={a.nombre} className="flex items-center gap-3">
                        <img
                          src={a.foto}
                          alt={a.nombre}
                          className="w-8 h-8 rounded-full object-cover border border-cine-line"
                        />
                        <span className="text-sm text-cine-cream">{a.nombre}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* ════════ OVERLAY SECUNDARIO — TRÁILER ════════ */}
      {trailerAbierto && embedUrl && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center"
          style={{ backgroundColor: "rgba(0,0,0,0.95)" }}
          onClick={() => setTrailerAbierto(false)}
        >
          {/* Panel del video */}
          <div
            className="relative w-full max-w-5xl rounded-xl overflow-hidden shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Barra superior oscura con botón cerrar — igual a la referencia */}
            <div
              className="flex items-center justify-end px-4 py-2"
              style={{ backgroundColor: "#111" }}
            >
              <button
                id="btn-cerrar-trailer"
                onClick={() => setTrailerAbierto(false)}
                className="flex items-center gap-2 text-xs font-semibold text-white hover:text-cine-gold transition-colors"
              >
                Cerrar &nbsp;✕
              </button>
            </div>

            {/* iframe del video */}
            <div className="w-full bg-black" style={{ aspectRatio: "16/9" }}>
              <iframe
                src={embedUrl}
                title="Tráiler"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowFullScreen
                className="w-full h-full border-0"
              />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
