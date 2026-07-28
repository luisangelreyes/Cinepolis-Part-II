import { useState } from "react";
import type { PeliculaCartelera } from "../types/api";
import { useNavigate } from "react-router-dom";
import { SinopsisModal } from "./SinopsisModal";

interface Props {
  pelicula: PeliculaCartelera;
}

function agruparPorIdioma(pelicula: PeliculaCartelera) {
  const grupos = new Map<string, typeof pelicula.funciones>();
  for (const f of pelicula.funciones) {
    const key = f.idioma;
    if (!grupos.has(key)) grupos.set(key, []);
    grupos.get(key)!.push(f);
  }
  return grupos;
}

function formatTime(timeStr: string) {
  const [h, m] = timeStr.split(":");
  let hour = parseInt(h, 10);
  const ampm = hour >= 12 ? "p.m." : "a.m.";
  hour = hour % 12;
  if (hour === 0) hour = 12;
  return `${hour}:${m} ${ampm}`;
}

function getSpecialFormat(formato: string, tipo_sala: string) {
  const tags = [];
  if (formato && formato.toUpperCase().includes("3D")) tags.push("3D");
  if (tipo_sala && tipo_sala.toUpperCase() !== "TRADICIONAL") tags.push(tipo_sala.toUpperCase());
  return tags.join(" ");
}

export function PeliculaCard({ pelicula }: Props) {
  const navigate = useNavigate();
  const grupos = agruparPorIdioma(pelicula);
  const [modalAbierto, setModalAbierto] = useState(false);

  return (
    <>
      <article className="flex flex-col sm:flex-row gap-6 bg-cine-bg border border-cine-line rounded-xl p-4 sm:p-6">
        <div className="w-32 sm:w-40 shrink-0 aspect-[2/3] rounded-lg overflow-hidden bg-cine-bg-raised border border-cine-line shadow-sm mx-auto sm:mx-0">
          {pelicula.poster_url ? (
            <img
              src={pelicula.poster_url}
              alt={`Póster de ${pelicula.titulo}`}
              className="w-full h-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-cine-slate text-xs px-2 text-center">
              Sin imagen
            </div>
          )}
        </div>

        <div className="flex-1 min-w-0 flex flex-col">
          <div className="flex items-start justify-between gap-2 text-center sm:text-left">
            <h3 className="font-display text-2xl sm:text-3xl leading-none tracking-wide text-cine-cream w-full">
              {pelicula.titulo}
            </h3>
          </div>

          <p className="text-cine-slate text-xs sm:text-sm mt-2 flex items-center justify-center sm:justify-start gap-2">
            <span className="shrink-0 text-[10px] font-bold bg-cine-gold text-cine-bg px-1.5 py-0.5 rounded">
              {pelicula.clasificacion}
            </span>
            <span>{pelicula.duracion_min} min</span>
          </p>

          {/* Botón Ver sinopsis — abre el modal */}
          <button
            id={`btn-sinopsis-${pelicula.pelicula_id}`}
            onClick={() => setModalAbierto(true)}
            className="text-cine-gold text-xs font-semibold mt-2 flex items-center justify-center sm:justify-start gap-1 hover:underline w-fit mx-auto sm:mx-0"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z" />
            </svg>
            Ver sinopsis
          </button>

          <div className="mt-6 space-y-5">
            {Array.from(grupos.entries()).map(([idioma, funciones]) => (
              <div key={idioma} className="space-y-3">
                <div className="bg-cine-line/30 rounded py-1.5 px-4 text-center">
                  <p className="text-xs font-bold text-cine-cream capitalize tracking-wide">
                    {idioma.toLowerCase()}
                  </p>
                </div>
                <div className="flex flex-wrap gap-3 justify-center sm:justify-start">
                  {funciones.map((f) => {
                    const tag = getSpecialFormat(f.formato, f.tipo_sala);
                    return (
                      <button
                        key={f.funcion_id}
                        onClick={() => navigate(`/funcion/${f.funcion_id}/asientos`)}
                        className="group flex flex-col items-center justify-center rounded-lg border border-cine-line bg-cine-bg-raised min-w-[100px] h-12 px-3 hover:border-cine-gold transition-colors"
                      >
                        {tag ? (
                          <span className="text-[8px] font-bold text-cine-slate uppercase tracking-wider leading-none mb-0.5">
                            {tag}
                          </span>
                        ) : null}
                        <span className="font-display font-semibold text-sm text-cine-cream group-hover:text-cine-gold leading-none">
                          {formatTime(f.hora_inicio)}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      </article>

      {/* Modal de sinopsis — montado fuera del article para evitar clipping */}
      {modalAbierto && (
        <SinopsisModal
          peliculaId={pelicula.pelicula_id}
          onClose={() => setModalAbierto(false)}
        />
      )}
    </>
  );
}
