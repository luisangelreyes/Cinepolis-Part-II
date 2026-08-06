import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { SeatMap } from "../components/SeatMap";
import { useAsientosFuncion, usePreciosFuncion } from "../hooks/useFuncion";
import { useAppStore } from "../store/useAppStore";
import { agregarAsientoCarrito, crearCarrito, getCarrito } from "../api/endpoints";
import type { AsientoAPI } from "../types/api";

/* ─── helpers ─── */
function formatFecha(fechaStr: string): string {
  if (!fechaStr) return "";
  const MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio",
                 "Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
  const [, m, d] = fechaStr.split("-");
  return `${parseInt(d)} de ${MESES[parseInt(m) - 1]}`;
}
function formatHora(horario: string): string {
  if (!horario) return "";
  const [h, min] = horario.split(":");
  let hour = parseInt(h, 10);
  const ampm = hour >= 12 ? "p.m." : "a.m.";
  hour = hour % 12 || 12;
  return `${hour}:${min} ${ampm}`;
}

/* ─── Modal de selección de boletos ─── */
interface ModalBoletosProps {
  tarifas: { tipo_boleto_id: number; tipo_boleto: string; precio: number; cargo_servicio: number; total_online: number }[];
  totalAsientos: number;
  onConfirmar: (asignacion: { tipo_boleto_id: number; total_online: number; tipo_boleto: string }[]) => void;
  onCerrar: () => void;
}

function ModalBoletos({ tarifas, totalAsientos, onConfirmar, onCerrar }: ModalBoletosProps) {
  const [cantidades, setCantidades] = useState<Record<number, number>>(() => {
    const init: Record<number, number> = {};
    tarifas.forEach(t => { init[t.tipo_boleto_id] = 0; });
    return init;
  });

  const totalAsignado = Object.values(cantidades).reduce((a, b) => a + b, 0);
  const restante = totalAsientos - totalAsignado;

  const setQty = (id: number, delta: number) => {
    setCantidades(prev => {
      const current = prev[id] ?? 0;
      const next = Math.max(0, current + delta);
      const otherTotal = Object.entries(prev)
        .filter(([k]) => Number(k) !== id)
        .reduce((a, [, v]) => a + v, 0);
      if (next + otherTotal > totalAsientos) return prev;
      return { ...prev, [id]: next };
    });
  };

  const handleConfirmar = () => {
    // Build a flat array of ticket assignments (one per asiento)
    const asignacion: { tipo_boleto_id: number; total_online: number; tipo_boleto: string }[] = [];
    tarifas.forEach(t => {
      const qty = cantidades[t.tipo_boleto_id] ?? 0;
      for (let i = 0; i < qty; i++) {
        asignacion.push({ tipo_boleto_id: t.tipo_boleto_id, total_online: t.total_online, tipo_boleto: t.tipo_boleto });
      }
    });
    onConfirmar(asignacion);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
      <div className="bg-cine-bg border border-cine-line rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-cine-line">
          <h2 className="font-display text-xl tracking-wide">Selecciona tus boletos</h2>
          <button onClick={onCerrar} className="text-cine-slate hover:text-cine-cream transition-colors text-2xl leading-none">×</button>
        </div>

        {/* Ticket types */}
        <div className="px-6 py-4">
          <p className="text-xs uppercase tracking-widest text-cine-slate mb-4 font-bold">Boletos</p>
          <div className="space-y-3">
            {tarifas.map(t => (
              <div key={t.tipo_boleto_id} className="flex items-center justify-between bg-cine-bg-raised border border-cine-line rounded-xl px-4 py-3">
                <div>
                  <p className="text-cine-cream font-semibold text-sm">{t.tipo_boleto}</p>
                  <p className="text-cine-gold font-mono text-sm">${t.total_online.toFixed(2)}</p>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setQty(t.tipo_boleto_id, -1)}
                    disabled={(cantidades[t.tipo_boleto_id] ?? 0) === 0}
                    className="w-8 h-8 rounded-full border border-cine-line text-cine-cream hover:border-cine-gold hover:text-cine-gold transition-colors disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center text-lg font-bold"
                  >
                    −
                  </button>
                  <span className="w-6 text-center font-mono text-cine-cream font-bold text-base">
                    {cantidades[t.tipo_boleto_id] ?? 0}
                  </span>
                  <button
                    onClick={() => setQty(t.tipo_boleto_id, 1)}
                    disabled={totalAsignado >= totalAsientos}
                    className="w-8 h-8 rounded-full bg-cine-gold text-cine-bg hover:bg-cine-gold/90 transition-colors disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center text-lg font-bold"
                  >
                    +
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 pb-6 space-y-3">
          <button
            onClick={handleConfirmar}
            disabled={restante !== 0}
            className="w-full bg-[#e31837] hover:bg-[#c41530] disabled:opacity-40 disabled:cursor-not-allowed transition-colors rounded-xl py-3.5 font-bold tracking-wide text-white text-sm"
          >
            Continuar
          </button>
          {restante !== 0 && (
            <p className="text-center text-xs text-cine-slate">
              {restante > 0
                ? `Falta(n) ${restante} boleto${restante > 1 ? "s" : ""} por seleccionar`
                : `Tienes ${Math.abs(restante)} boleto${Math.abs(restante) > 1 ? "s" : ""} de más`}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Main Page ─── */
export function SeatSelectionPage() {
  const { funcionId } = useParams();
  const fid = Number(funcionId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: mapaData, isLoading, isError, error } = useAsientosFuncion(fid);
  const { data: preciosData } = usePreciosFuncion(fid);
  const complejoSlug = useAppStore((s) => s.complejoSlug);
  const carritoId = useAppStore((s) => s.carritoId);
  const setCarritoId = useAppStore((s) => s.setCarritoId);

  // LOCAL selection state (not yet in cart)
  const [preSeleccion, setPreSeleccion] = useState<Set<number>>(new Set());
  // Already-confirmed (in cart) items for rehydration display
  const [confirmedItems, setConfirmedItems] = useState<{ asiento_id: number; etiqueta: string; tipo: string; precio: number }[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);

  const { data: carritoData } = useQuery({
    queryKey: ["carrito", carritoId],
    queryFn: () => getCarrito(carritoId!),
    enabled: !!carritoId,
    retry: false,
  });

  // Rehydrate confirmed items from cart (on reload)
  useEffect(() => {
    if (carritoData && mapaData) {
      const flatAsientos = Object.values(mapaData.mapa).flat();
      const asientosEnMapa = new Map(flatAsientos.map((a: any) => [a.asiento_id, a]));
      const items = carritoData.items
        .filter(i => i.tipo_item === "boleto" && i.asiento_id && asientosEnMapa.has(i.asiento_id))
        .map(i => {
          const a = asientosEnMapa.get(i.asiento_id!) as any;
          const tarifa = preciosData?.tarifas.find(t => t.tipo_boleto_id === i.tipo_boleto_id);
          return {
            asiento_id: i.asiento_id!,
            etiqueta: a.etiqueta,
            tipo: tarifa?.tipo_boleto ?? "Boleto",
            precio: Number(i.precio_unitario),
          };
        });
      setConfirmedItems(items);
    }
  }, [carritoData, mapaData, preciosData]);

  const mutAgregar = useMutation({
    mutationFn: async (payload: { asientos: AsientoAPI[]; asignacion: { tipo_boleto_id: number; total_online: number; tipo_boleto: string }[] }) => {
      let cid = carritoId;
      if (!cid) {
        const nuevo = await crearCarrito({});
        cid = nuevo.carrito_id;
        setCarritoId(cid, fid);
      }
      // Add each seat to cart with its assigned type
      const results = [];
      for (let i = 0; i < payload.asientos.length; i++) {
        const asiento = payload.asientos[i];
        const tipo = payload.asignacion[i];
        const res = await agregarAsientoCarrito(cid, {
          asiento_id: asiento.asiento_id,
          tipo_boleto_id: tipo.tipo_boleto_id,
          precio_unitario: tipo.total_online,
        });
        results.push({ asiento, tipo, detalleCarritoId: res.detalle_carrito_id });
      }
      return { results, cid };
    },
    onSuccess: ({ results, cid }) => {
      const newItems = results.map(r => ({
        asiento_id: r.asiento.asiento_id,
        etiqueta: r.asiento.etiqueta,
        tipo: r.tipo.tipo_boleto,
        precio: r.tipo.total_online,
      }));
      setConfirmedItems(prev => [...prev, ...newItems]);
      setPreSeleccion(new Set());
      queryClient.invalidateQueries({ queryKey: ["carrito", cid] });
      queryClient.invalidateQueries({ queryKey: ["asientos", fid] });
      setErrorAccion(null);
    },
    onError: (e: Error) => {
      setErrorAccion(e.message);
      if (e.message.toLowerCase().includes("abandonado") || e.message.toLowerCase().includes("expiró")) {
        setCarritoId(null);
        setPreSeleccion(new Set());
        setConfirmedItems([]);
      }
    },
  });

  const handleToggle = (asiento: AsientoAPI) => {
    setErrorAccion(null);
    // Only allow toggling local pre-selection (not already-confirmed items)
    const isConfirmed = confirmedItems.some(c => c.asiento_id === asiento.asiento_id);
    if (isConfirmed) return; // Already added to cart, ignore
    setPreSeleccion(prev => {
      const next = new Set(prev);
      if (next.has(asiento.asiento_id)) next.delete(asiento.asiento_id);
      else next.add(asiento.asiento_id);
      return next;
    });
  };

  const handleConfirmarBoletos = async (
    asignacion: { tipo_boleto_id: number; total_online: number; tipo_boleto: string }[]
  ) => {
    if (!mapaData) return;
    const flatAsientos = Object.values(mapaData.mapa).flat() as AsientoAPI[];
    const asientosSeleccionados = flatAsientos.filter(a => preSeleccion.has(a.asiento_id));
    setProcesando(true);
    setShowModal(false);
    try {
      await mutAgregar.mutateAsync({ asientos: asientosSeleccionados, asignacion });
    } finally {
      setProcesando(false);
    }
  };

  // Combine confirmed + preSelection for display in the map
  const allSelectedIds = useMemo(() => {
    const ids = new Set(preSeleccion);
    confirmedItems.forEach(c => ids.add(c.asiento_id));
    return ids;
  }, [preSeleccion, confirmedItems]);

  const subtotal = useMemo(() => confirmedItems.reduce((acc, c) => acc + c.precio, 0), [confirmedItems]);
  const tarifas = preciosData?.tarifas ?? [];

  // Group confirmed items by type
  const confirmedAgrupados = useMemo(() => {
    const grupos: Record<string, { count: number; precio: number }> = {};
    confirmedItems.forEach(c => {
      if (!grupos[c.tipo]) grupos[c.tipo] = { count: 0, precio: c.precio };
      grupos[c.tipo].count++;
    });
    return grupos;
  }, [confirmedItems]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-cine-slate font-mono animate-pulse">Cargando sala…</p>
      </div>
    );
  }

  if (isError || !mapaData) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-10">
        <p className="text-cine-crimson font-semibold">No se pudo cargar el mapa de asientos.</p>
        <p className="text-cine-slate text-sm mt-1">{(error as Error)?.message}</p>
      </div>
    );
  }

  const posterFallback = `https://placehold.co/60x80/1a1d2e/c8a96a?text=${encodeURIComponent(mapaData.pelicula.slice(0, 2))}`;

  return (
    <>
      {showModal && tarifas.length > 0 && (
        <ModalBoletos
          tarifas={tarifas}
          totalAsientos={preSeleccion.size}
          onConfirmar={handleConfirmarBoletos}
          onCerrar={() => setShowModal(false)}
        />
      )}

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-cine-slate mb-6 font-mono">
          <button onClick={() => navigate(-1)} className="hover:text-cine-gold transition-colors">← Horario</button>
          <span className="text-cine-line">›</span>
          <span className="text-cine-cream font-bold">Asientos</span>
          <span className="text-cine-line">›</span>
          <span>Pago</span>
        </div>

        <div className="grid lg:grid-cols-[1fr_320px] gap-6 items-start">
          {/* ── LEFT: Seat Map ── */}
          <div>
            {/* Horario pill */}
            <div className="flex gap-3 mb-5">
              <button className="px-4 py-2 rounded-lg font-mono text-sm font-bold border-2 border-cine-gold text-cine-gold bg-cine-gold/10">
                {formatHora(mapaData.horario)}
              </button>
            </div>

            <div className="bg-cine-bg-raised border border-cine-line rounded-xl p-5">
              <SeatMap mapa={mapaData.mapa} seleccionados={allSelectedIds} onToggle={handleToggle} />
              {errorAccion && (
                <p className="mt-4 text-sm text-cine-crimson border border-cine-crimson/50 rounded-lg px-3 py-2 text-center">
                  {errorAccion}
                </p>
              )}
            </div>
          </div>

          {/* ── RIGHT: "Tu carrito" sidebar ── */}
          <aside className="lg:sticky lg:top-6 h-fit">
            <div className="bg-cine-bg-raised border border-cine-line rounded-xl overflow-hidden shadow-2xl">
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 bg-cine-gold/10 border-b border-cine-line">
                <div className="flex items-center gap-2">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-cine-gold" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M3 1a1 1 0 000 2h1.22l.305 1.222a.997.997 0 00.01.042l1.358 5.43-.893.892C3.74 11.846 4.632 14 6.414 14H15a1 1 0 000-2H6.414l1-1H14a1 1 0 00.894-.553l3-6A1 1 0 0017 3H6.28l-.31-1.243A1 1 0 005 1H3zM16 16.5a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zM6.5 18a1.5 1.5 0 100-3 1.5 1.5 0 000 3z" />
                  </svg>
                  <span className="text-sm font-bold text-cine-cream uppercase tracking-wide">Tu carrito</span>
                </div>
                <span className="font-display text-lg text-cine-gold">${subtotal.toFixed(2)}</span>
              </div>

              {/* Movie info */}
              <div className="p-4 border-b border-cine-line flex gap-3">
                <img
                  src={mapaData.poster_url || posterFallback}
                  alt={mapaData.pelicula}
                  className="w-14 h-20 object-cover rounded-md flex-shrink-0 border border-cine-line"
                  onError={(e) => { (e.target as HTMLImageElement).src = posterFallback; }}
                />
                <div className="min-w-0">
                  <p className="font-bold text-cine-cream text-sm leading-tight mb-2 line-clamp-2">{mapaData.pelicula}</p>
                  <div className="flex items-center gap-2 flex-wrap">
                    {mapaData.clasificacion && (
                      <span className="text-[10px] font-bold border border-cine-gold/70 text-cine-gold px-1.5 py-0.5 rounded">
                        {mapaData.clasificacion}
                      </span>
                    )}
                    {mapaData.duracion_min && (
                      <span className="text-[10px] text-cine-slate font-mono">{mapaData.duracion_min} min</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Function details */}
              <div className="px-4 py-3 border-b border-cine-line space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-cine-slate">Fecha y hora</span>
                  <span className="text-cine-cream-dim font-medium text-right">
                    {formatFecha(mapaData.fecha_funcion)} · {formatHora(mapaData.horario)}
                  </span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-cine-slate">Sala</span>
                  <span className="text-cine-cream-dim font-medium">{mapaData.sala}</span>
                </div>
              </div>

              {/* Seats section */}
              <div className="px-4 py-3 border-b border-cine-line min-h-[80px]">
                <p className="text-[10px] text-cine-slate uppercase font-bold tracking-widest mb-3">
                  Asientos ({confirmedItems.length}{preSeleccion.size > 0 ? ` + ${preSeleccion.size} pendiente${preSeleccion.size > 1 ? "s" : ""}` : ""})
                </p>

                {confirmedItems.length === 0 && preSeleccion.size === 0 ? (
                  <div className="flex items-center gap-2 text-cine-slate text-xs py-2 bg-cine-bg rounded-lg px-3">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 opacity-50 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                    <span>No has seleccionado tus asientos</span>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {/* Confirmed items grouped */}
                    {Object.entries(confirmedAgrupados).map(([tipo, info]) => (
                      <div key={tipo} className="flex items-center gap-2 text-sm">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-cine-slate flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                        </svg>
                        <span className="text-cine-cream">{tipo}</span>
                        <span className="text-cine-slate">· {info.count} persona{info.count > 1 ? "s" : ""}</span>
                      </div>
                    ))}
                    {/* Etiquetas */}
                    {confirmedItems.length > 0 && (
                      <p className="text-[10px] text-cine-slate font-mono mt-1">
                        {confirmedItems.map(c => c.etiqueta).join(", ")}
                      </p>
                    )}
                    {/* Pre-selected pending */}
                    {preSeleccion.size > 0 && (
                      <div className="text-xs text-cine-gold/80 bg-cine-gold/10 rounded-lg px-2 py-1.5 border border-cine-gold/20">
                        {preSeleccion.size} asiento{preSeleccion.size > 1 ? "s" : ""} pendiente{preSeleccion.size > 1 ? "s" : ""} de asignar tipo
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Alimentos section */}
              <div className="px-4 py-3 border-b border-cine-line">
                <p className="text-[10px] text-cine-slate uppercase font-bold tracking-widest mb-2">
                  Alimentos (0)
                </p>
                <div className="flex items-center gap-2 text-cine-slate text-xs py-2 bg-cine-bg rounded-lg px-3">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 opacity-50 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 2a8 8 0 100 16A8 8 0 0010 2zm1 5a1 1 0 10-2 0v4a1 1 0 102 0V7zm-1 8a1.5 1.5 0 100-3 1.5 1.5 0 000 3z" clipRule="evenodd" />
                  </svg>
                  <span>No has agregado alimentos a tu orden</span>
                </div>
              </div>

              {/* Subtotal (only shown when there are confirmed items) */}
              {confirmedItems.length > 0 && (
                <div className="px-4 py-3 border-b border-cine-line flex justify-between items-baseline">
                  <span className="text-cine-slate text-sm">Subtotal</span>
                  <span className="font-display text-xl text-cine-gold">${subtotal.toFixed(2)}</span>
                </div>
              )}

              {/* CTA Buttons */}
              <div className="p-4 space-y-2">
                {/* Primary: open ticket type modal if pre-selection exists */}
                {preSeleccion.size > 0 && (
                  <button
                    disabled={procesando}
                    onClick={() => setShowModal(true)}
                    className="w-full bg-[#e31837] hover:bg-[#c41530] disabled:opacity-40 transition-colors rounded-xl py-3.5 font-bold tracking-wide text-white text-sm shadow-md"
                  >
                    {procesando ? "Guardando…" : "Seleccionar mis boletos"}
                  </button>
                )}

                {/* Continue to dulcería if there are confirmed items in cart */}
                {confirmedItems.length > 0 && preSeleccion.size === 0 && (
                  <button
                    onClick={() => navigate("/carrito")}
                    className="w-full bg-[#e31837] hover:bg-[#c41530] transition-colors rounded-xl py-3.5 font-bold tracking-wide text-white text-sm shadow-md"
                  >
                    Continuar con dulcería
                  </button>
                )}

                {/* Go back */}
                <button
                  onClick={() => navigate(-1)}
                  className="w-full bg-transparent border border-cine-line text-cine-slate hover:text-cine-cream hover:border-cine-cream-dim transition-colors rounded-xl py-3 font-semibold text-sm"
                >
                  Volver
                </button>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </>
  );
}
