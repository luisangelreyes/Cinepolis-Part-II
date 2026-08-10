import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAppStore } from "../store/useAppStore";
import { getDulceria, getCarrito, eliminarItemCarrito } from "../api/endpoints";
import { useAsientosFuncion, usePreciosFuncion } from "../hooks/useFuncion";

interface CartSummaryProps {
  onClose?: () => void;
}

export function CartSummary({ onClose }: CartSummaryProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const complejoSlug = useAppStore((s) => s.complejoSlug);
  const carritoId = useAppStore((s) => s.carritoId);
  const carritoFuncionId = useAppStore((s) => s.carritoFuncionId);
  const setIsCartOpen = useAppStore((s) => s.setIsCartOpen);

  const handleClose = () => {
    if (onClose) onClose();
    else setIsCartOpen(false);
  };

  const { data: menuData } = useQuery({
    queryKey: ["dulceria", complejoSlug],
    queryFn: () => getDulceria(complejoSlug),
  });
  
  const { data: carritoData } = useQuery({
    queryKey: ["carrito", carritoId],
    queryFn: () => getCarrito(carritoId!),
    enabled: !!carritoId,
  });

  const { data: mapaData } = useAsientosFuncion(carritoFuncionId || 0);
  const { data: preciosData } = usePreciosFuncion(carritoFuncionId || 0);

  const mutEliminar = useMutation({
    mutationFn: (detalleId: number) => eliminarItemCarrito(carritoId!, detalleId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["carrito"] }),
  });

  // Boletos confirmados para mostrar en sidebar
  const boletosEnCarrito = useMemo(() => {
    if (!carritoData || !mapaData || !preciosData) return [];
    const flatAsientos = Object.values(mapaData.mapa).flat();
    const asientosMap = new Map(flatAsientos.map((a: any) => [a.asiento_id, a]));
    return carritoData.items
      .filter((i: any) => i.tipo_item === "boleto")
      .map((i: any) => {
        const a = asientosMap.get(i.asiento_id) as any;
        const tarifa = preciosData.tarifas.find(t => t.tipo_boleto_id === i.tipo_boleto_id);
        return {
          etiqueta: a?.etiqueta ?? `ID ${i.asiento_id}`,
          tipo: tarifa?.tipo_boleto ?? "Boleto",
          precio: Number(i.precio_unitario),
        };
      });
  }, [carritoData, mapaData, preciosData]);

  // Items de dulcería en carrito (con nombre)
  const productosEnCarrito = useMemo(() => {
    if (!carritoData || !menuData) return [];
    const flatProductos = menuData.menu.flatMap((c: any) => c.productos);
    const productosMap = new Map(flatProductos.map((p: any) => [p.producto_id, p]));
    
    return carritoData.items
      .filter((i: any) => i.tipo_item === "producto" && i.producto_id != null)
      .map((i: any) => {
        const prod = productosMap.get(i.producto_id) as any;
        return {
          detalle_carrito_id: i.detalle_carrito_id,
          nombre: prod?.nombre ?? `Producto ${i.producto_id}`,
          cantidad: i.cantidad,
          precio: Number(i.precio_unitario),
          personalizaciones: i.personalizaciones || [],
        };
      });
  }, [carritoData, menuData]);

  const subtotalDulceria = productosEnCarrito.reduce((a, p) => a + p.precio * p.cantidad, 0);
  const subtotalBoletos = boletosEnCarrito.reduce((a, b) => a + b.precio, 0);
  const subtotal = subtotalBoletos + subtotalDulceria;

  const posterFallback = mapaData
    ? `https://placehold.co/60x80/1a1d2e/c8a96a?text=${encodeURIComponent(mapaData.pelicula.slice(0, 2))}`
    : "";

  return (
    <div className="bg-cine-bg-raised border border-cine-line rounded-xl overflow-hidden shadow-2xl h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-[#0a182b] border-b border-cine-line shrink-0">
        <div className="flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-cine-gold" viewBox="0 0 20 20" fill="currentColor">
            <path d="M3 1a1 1 0 000 2h1.22l.305 1.222a.997.997 0 00.01.042l1.358 5.43-.893.892C3.74 11.846 4.632 14 6.414 14H15a1 1 0 000-2H6.414l1-1H14a1 1 0 00.894-.553l3-6A1 1 0 0017 3H6.28l-.31-1.243A1 1 0 005 1H3zM16 16.5a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zM6.5 18a1.5 1.5 0 100-3 1.5 1.5 0 000 3z" />
          </svg>
          <span className="text-sm font-bold text-white uppercase tracking-wide">Tu carrito</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="font-display text-lg text-white">${subtotal.toFixed(2)}</span>
          {onClose && (
            <button onClick={handleClose} className="text-cine-slate hover:text-white transition-colors">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {/* Movie info (only if active ticket) */}
        {mapaData && (
          <div className="p-4 border-b border-cine-line flex gap-3 bg-cine-bg">
            <img
              src={mapaData.poster_url || posterFallback}
              alt={mapaData.pelicula}
              className="w-12 h-16 object-cover rounded-md flex-shrink-0 border border-cine-line"
              onError={(e) => { (e.target as HTMLImageElement).src = posterFallback; }}
            />
            <div className="min-w-0">
              <p className="font-bold text-cine-cream text-sm leading-tight mb-1.5 line-clamp-2">{mapaData.pelicula}</p>
              <div className="flex items-center gap-2 flex-wrap">
                {mapaData.clasificacion && (
                  <span className="text-[9px] font-bold border border-[#009c4a] text-[#009c4a] bg-[#009c4a]/10 px-1.5 py-0.5 rounded">
                    {mapaData.clasificacion}
                  </span>
                )}
                <span className="text-[9px] text-cine-slate font-mono">{mapaData.sala}</span>
              </div>
            </div>
          </div>
        )}

        {/* Boletos (only if they exist) */}
        {boletosEnCarrito.length > 0 && (
          <div className="px-4 py-3 border-b border-cine-line">
            <p className="text-[10px] text-cine-slate uppercase font-bold tracking-widest mb-2">
              Boletos ({boletosEnCarrito.length})
            </p>
            <div className="space-y-1.5">
              {boletosEnCarrito.map((b, idx) => (
                <div key={idx} className="flex justify-between text-xs">
                  <span className="text-cine-cream-dim">{b.tipo} · {b.etiqueta}</span>
                  <span className="font-mono text-cine-gold">${b.precio.toFixed(2)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Alimentos */}
        <div className="px-4 py-3 border-b border-cine-line min-h-[60px]">
          <p className="text-[10px] text-cine-slate uppercase font-bold tracking-widest mb-2">
            Alimentos ({productosEnCarrito.reduce((a, p) => a + p.cantidad, 0)})
          </p>
          {productosEnCarrito.length === 0 ? (
            <div className="flex items-center gap-2 text-cine-slate text-xs py-1.5 bg-cine-bg rounded-lg px-3">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 opacity-50 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 2a8 8 0 100 16A8 8 0 0010 2zm1 5a1 1 0 10-2 0v4a1 1 0 102 0V7zm-1 8a1.5 1.5 0 100-3 1.5 1.5 0 000 3z" clipRule="evenodd" />
              </svg>
              <span>No has agregado alimentos</span>
            </div>
          ) : (
            <div className="space-y-3">
              {productosEnCarrito.map((p, idx) => (
                <div key={idx} className="flex flex-col gap-1 border-b border-cine-line/30 pb-2 last:border-0 last:pb-0">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <button
                        onClick={() => mutEliminar.mutate(p.detalle_carrito_id)}
                        className="w-4 h-4 rounded-full bg-cine-slate/20 hover:bg-red-500/20 text-cine-slate hover:text-red-500 flex items-center justify-center transition-colors flex-shrink-0"
                        disabled={mutEliminar.isPending}
                      >
                        <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M20 12H4" />
                        </svg>
                      </button>
                      <span className="font-bold text-xs text-cine-cream-dim bg-cine-slate/20 px-1.5 rounded">{p.cantidad}</span>
                      <span className="text-xs font-semibold text-cine-cream-dim truncate">{p.nombre}</span>
                    </div>
                    <span className="font-mono text-xs text-cine-gold flex-shrink-0">${(p.precio * p.cantidad).toFixed(2)}</span>
                  </div>
                  
                  {/* Personalizations (Flavors, Sizes, etc.) */}
                  {p.personalizaciones && p.personalizaciones.length > 0 && (
                    <div className="pl-6 text-[10px] text-cine-slate/80 space-y-0.5">
                      {p.personalizaciones.map((pers: any, i: number) => (
                        <div key={i} className="flex items-center gap-1.5">
                          <span className="w-1 h-1 rounded-full bg-cine-slate/50"></span>
                          <span className="truncate max-w-[150px]">{pers.nombre_opcion}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Subtotal y CTA */}
      <div className="p-4 shrink-0 bg-cine-bg-raised mt-auto">
        <div className="flex justify-between text-sm mb-4">
          <span className="text-cine-slate">Subtotal</span>
          <span className="font-display text-lg text-cine-gold">${subtotal.toFixed(2)}</span>
        </div>
        <button
          onClick={() => {
            handleClose();
            navigate("/checkout");
          }}
          disabled={productosEnCarrito.length === 0 && boletosEnCarrito.length === 0}
          className="w-full bg-[#e31837] hover:bg-[#c41530] disabled:opacity-40 disabled:cursor-not-allowed transition-colors rounded-xl py-3.5 font-bold tracking-wide text-white text-sm shadow-md"
        >
          Proceder al pago
        </button>
        {boletosEnCarrito.length > 0 && (
          <button
            onClick={() => {
              handleClose();
              navigate("/checkout");
            }}
            className="w-full mt-2 text-cine-slate hover:text-cine-cream text-xs py-2 transition-colors"
          >
            Omitir dulcería →
          </button>
        )}
      </div>
    </div>
  );
}
