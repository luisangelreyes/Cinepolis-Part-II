import { useState } from "react";
import type { PeliculaCartelera } from "../types/api";
import { useNavigate } from "react-router-dom";
import { SinopsisModal } from "./SinopsisModal";
import { useAppStore } from "../store/useAppStore";

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
  const ampm = hour >= 12 ? "PM" : "AM";
  hour = hour % 12 || 12;
  return `${hour}:${m} ${ampm}`;
}

function getSpecialFormat(formato: string, tipoSala: string) {
  const sala = tipoSala.toLowerCase();
  const fmt = formato.toUpperCase();
  const tags: string[] = [];

  // Experience badges (from tipo_sala)
  if (sala.includes("4dx")) tags.push("4DX");
  else if (sala.includes("macro") && sala.includes("xe")) tags.push("MACRO XE");
  else if (sala.includes("imax")) tags.push("IMAX");
  else if (sala.includes("vip")) tags.push("VIP");
  else if (sala.includes("junior")) tags.push("junior");

  // Format badges (from formato)
  if (fmt === "3D" || fmt === "IMAX 3D") tags.push(fmt);

  if (tags.length === 0) return null;
  return tags.join(" ");
}

export function PeliculaCard({ pelicula }: Props) {
  const navigate = useNavigate();
  const grupos = agruparPorIdioma(pelicula);
  const [modalAbierto, setModalAbierto] = useState(false);
  const [funcionPendiente, setFuncionPendiente] = useState<number | null>(null);
  const carritoId = useAppStore((s) => s.carritoId);
  const carritoFuncionId = useAppStore((s) => s.carritoFuncionId);
  const setCarritoId = useAppStore((s) => s.setCarritoId);

  const handleFunctionClick = (funcionId: number) => {
    if (carritoId && carritoFuncionId !== funcionId) {
      setFuncionPendiente(funcionId);
    } else {
      navigate(`/funcion/${funcionId}/asientos`);
    }
  };

  const confirmarCambio = () => {
    setCarritoId(null);
    if (funcionPendiente) {
      navigate(`/funcion/${funcionPendiente}/asientos`);
    }
  };

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
                        onClick={() => handleFunctionClick(f.funcion_id)}
                        className="group flex flex-col items-center justify-center rounded-lg border border-cine-line bg-cine-bg-raised min-w-[100px] h-12 px-3 hover:border-cine-gold transition-colors"
                      >
                        {tag && (
                          <span className="text-[9px] font-bold text-cine-gold tracking-wider mb-0.5 opacity-80 group-hover:opacity-100 transition-opacity">
                            {tag}
                          </span>
                        )}
                        <span className="text-sm font-mono text-cine-cream group-hover:text-cine-gold transition-colors">
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

      {modalAbierto && (
        <SinopsisModal
          peliculaId={pelicula.pelicula_id}
          onClose={() => setModalAbierto(false)}
        />
      )}

      {funcionPendiente && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl w-full max-w-lg p-8 shadow-2xl relative animate-in fade-in zoom-in duration-200">
            <h2 className="text-[#002f6c] text-2xl font-bold text-center mb-4">
              ¿Estás seguro que deseas cambiar tu película?
            </h2>
            <p className="text-gray-500 text-center mb-8 text-sm">
              Al cambiar tu película, todos los productos en tu carrito se perderán automáticamente.
            </p>
            <div className="flex flex-col gap-3">
              <button
                onClick={confirmarCambio}
                className="w-full bg-[#4887ff] hover:bg-[#356edb] text-white font-semibold py-3.5 rounded-xl transition-colors text-sm"
              >
                Aceptar
              </button>
              <button
                onClick={() => setFuncionPendiente(null)}
                className="w-full bg-gray-100 hover:bg-gray-200 text-[#002f6c] font-semibold py-3.5 rounded-xl transition-colors text-sm"
              >
                Continuar compra
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
