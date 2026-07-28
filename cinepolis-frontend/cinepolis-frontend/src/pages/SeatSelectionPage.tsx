import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { SeatMap } from "../components/SeatMap";
import { useAsientosFuncion, usePreciosFuncion } from "../hooks/useFuncion";
import { useAppStore } from "../store/useAppStore";
import { agregarAsientoCarrito, crearCarrito, eliminarItemCarrito } from "../api/endpoints";
import type { AsientoAPI } from "../types/api";

interface SeleccionItem {
  detalleCarritoId: number;
  etiqueta: string;
  precio: number;
}

export function SeatSelectionPage() {
  const { funcionId } = useParams();
  const fid = Number(funcionId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: mapaData, isLoading, isError, error } = useAsientosFuncion(fid);
  const { data: preciosData } = usePreciosFuncion(fid);

  const carritoId = useAppStore((s) => s.carritoId);
  const setCarritoId = useAppStore((s) => s.setCarritoId);

  const [tipoBoletoId, setTipoBoletoId] = useState<number | null>(null);
  const [seleccion, setSeleccion] = useState<Map<number, SeleccionItem>>(new Map());
  const [errorAccion, setErrorAccion] = useState<string | null>(null);

  const tarifas = preciosData?.tarifas ?? [];
  const tarifaActiva = tarifas.find((t) => t.tipo_boleto_id === tipoBoletoId) ?? tarifas[0];

  const mutAgregar = useMutation({
    mutationFn: async (asiento: AsientoAPI) => {
      let cid = carritoId;
      if (!cid) {
        const nuevo = await crearCarrito({});
        cid = nuevo.carrito_id;
        setCarritoId(cid);
      }
      if (!tarifaActiva) throw new Error("Selecciona primero un tipo de boleto.");
      const res = await agregarAsientoCarrito(cid, {
        asiento_id: asiento.asiento_id,
        tipo_boleto_id: tarifaActiva.tipo_boleto_id,
        precio_unitario: tarifaActiva.total_online,
      });
      return { asiento, detalleCarritoId: res.detalle_carrito_id as number };
    },
    onSuccess: ({ asiento, detalleCarritoId }) => {
      setSeleccion((prev) => {
        const next = new Map(prev);
        next.set(asiento.asiento_id, {
          detalleCarritoId,
          etiqueta: asiento.etiqueta,
          precio: tarifaActiva?.total_online ?? 0,
        });
        return next;
      });
      setErrorAccion(null);
    },
    onError: (e: Error) => setErrorAccion(e.message),
  });

  const mutQuitar = useMutation({
    mutationFn: async ({ asientoId, detalleCarritoId }: { asientoId: number; detalleCarritoId: number }) => {
      if (!carritoId) return;
      await eliminarItemCarrito(carritoId, detalleCarritoId);
      return asientoId;
    },
    onSuccess: (asientoId) => {
      if (!asientoId) return;
      setSeleccion((prev) => {
        const next = new Map(prev);
        next.delete(asientoId);
        return next;
      });
      queryClient.invalidateQueries({ queryKey: ["asientos", fid] });
    },
    onError: (e: Error) => setErrorAccion(e.message),
  });

  const handleToggle = (asiento: AsientoAPI) => {
    setErrorAccion(null);
    const yaSeleccionado = seleccion.get(asiento.asiento_id);
    if (yaSeleccionado) {
      mutQuitar.mutate({ asientoId: asiento.asiento_id, detalleCarritoId: yaSeleccionado.detalleCarritoId });
    } else {
      if (!tarifaActiva) {
        setErrorAccion("Selecciona primero un tipo de boleto en el panel derecho.");
        return;
      }
      mutAgregar.mutate(asiento);
    }
  };

  const seleccionadosIds = useMemo(() => new Set(seleccion.keys()), [seleccion]);
  const subtotal = useMemo(
    () => Array.from(seleccion.values()).reduce((acc, s) => acc + s.precio, 0),
    [seleccion]
  );

  if (isLoading) {
    return <div className="max-w-5xl mx-auto px-4 py-10 text-cine-slate font-mono">Cargando sala…</div>;
  }

  if (isError || !mapaData) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-10">
        <p className="text-cine-crimson font-semibold">No se pudo cargar el mapa de asientos.</p>
        <p className="text-cine-slate text-sm mt-1">{(error as Error)?.message}</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 grid lg:grid-cols-[1fr_320px] gap-8">
      <div>
        <button
          onClick={() => navigate(-1)}
          className="text-cine-slate text-sm mb-4 hover:text-cine-gold transition-colors"
        >
          ← Volver a cartelera
        </button>

        <h1 className="font-display text-4xl tracking-wide leading-none">{mapaData.pelicula}</h1>
        <p className="text-cine-slate text-sm mt-1 font-mono">
          {mapaData.sala} · {mapaData.horario.slice(0, 5)} · {mapaData.asientos_disponibles} disponibles
        </p>

        <div className="mt-8 bg-cine-bg-raised border border-cine-line rounded-xl p-6">
          <SeatMap mapa={mapaData.mapa} seleccionados={seleccionadosIds} onToggle={handleToggle} />
        </div>

        {errorAccion && (
          <p className="mt-4 text-sm text-cine-crimson border border-cine-crimson rounded-lg px-3 py-2">
            {errorAccion}
          </p>
        )}
      </div>

      <aside className="bg-cine-bg-raised border border-cine-line rounded-xl p-5 h-fit lg:sticky lg:top-8">
        <h2 className="font-display text-2xl tracking-wide mb-3">Tu boleto</h2>

        <label className="block text-xs uppercase tracking-wide text-cine-slate mb-1.5">
          Tipo de boleto
        </label>
        <select
          value={tarifaActiva?.tipo_boleto_id ?? ""}
          onChange={(e) => setTipoBoletoId(Number(e.target.value))}
          className="w-full bg-cine-bg border border-cine-line rounded-md px-3 py-2 text-sm mb-5 focus:border-cine-gold outline-none"
        >
          <option value="" disabled>
            Elige una tarifa…
          </option>
          {tarifas.map((t) => (
            <option key={t.tipo_boleto_id} value={t.tipo_boleto_id}>
              {t.tipo_boleto} · ${t.total_online.toFixed(2)}
            </option>
          ))}
        </select>

        <div className="space-y-1.5 mb-4 min-h-[2rem]">
          {Array.from(seleccion.values()).length === 0 && (
            <p className="text-cine-slate text-sm">Aún no seleccionas asientos.</p>
          )}
          {Array.from(seleccion.values()).map((s) => (
            <div key={s.detalleCarritoId} className="flex justify-between text-sm font-mono">
              <span className="text-cine-cream">{s.etiqueta}</span>
              <span className="text-cine-cream-dim">${s.precio.toFixed(2)}</span>
            </div>
          ))}
        </div>

        <div className="border-t border-cine-line pt-3 flex justify-between items-baseline mb-5">
          <span className="text-cine-slate text-sm">Subtotal</span>
          <span className="font-display text-3xl text-cine-gold">${subtotal.toFixed(2)}</span>
        </div>

        <button
          disabled={seleccion.size === 0}
          onClick={() => navigate("/carrito")}
          className="w-full bg-cine-crimson hover:bg-cine-crimson-dim disabled:opacity-40 disabled:cursor-not-allowed transition-colors rounded-md py-3 font-body font-semibold tracking-wide"
        >
          Continuar con dulcería
        </button>
      </aside>
    </div>
  );
}
