import { useState, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAppStore } from "../store/useAppStore";
import { getDulceria, getCarrito, agregarProductoCarrito, eliminarItemCarrito } from "../api/endpoints";
import { useAsientosFuncion, usePreciosFuncion } from "../hooks/useFuncion";
import type { ProductoDulceria } from "../types/api";
import { ModalPersonalizacion } from "../components/ModalPersonalizacion";


/* ─── Tarjeta de Producto ─── */
interface ProductoCardProps {
  producto: ProductoDulceria;
  cantidadEnCarrito: number;
  onAgregar: () => void;
  onQuitar: () => void;
  isLoading: boolean;
}

function ProductoCard({ producto, cantidadEnCarrito, onAgregar, onQuitar, isLoading }: ProductoCardProps) {
  return (
    <article className="w-[200px] sm:w-[240px] shrink-0 bg-cine-bg-raised border border-cine-line rounded-xl overflow-hidden flex flex-col hover:border-cine-gold/40 transition-all snap-start group">
      <div className="aspect-[4/3] bg-cine-line/30 relative overflow-hidden">
        {producto.imagen_url ? (
          <img
            src={producto.imagen_url}
            alt={producto.nombre}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-cine-slate text-xs">Sin imagen</div>
        )}
        {producto.personalizacion.length > 0 && (
          <span className="absolute top-2 left-2 bg-cine-gold text-cine-bg text-[9px] font-black px-1.5 py-0.5 rounded-full uppercase tracking-wider">
            Personalizable
          </span>
        )}
      </div>
      <div className="p-3 flex flex-col flex-1">
        <h3 className="font-bold text-cine-cream text-sm leading-tight mb-1 line-clamp-2">{producto.nombre}</h3>
        <p className="text-cine-slate text-[10px] mb-3 line-clamp-2 flex-1 leading-relaxed">{producto.descripcion}</p>

        <div className="flex items-center justify-between mt-auto pt-2 border-t border-cine-line/50">
          <span className="font-mono text-base text-cine-gold font-bold">${producto.precio.toFixed(2)}</span>

          {cantidadEnCarrito === 0 ? (
            <button
              onClick={onAgregar}
              disabled={isLoading}
              className="bg-cine-gold text-cine-bg hover:bg-[#e5b33e] disabled:opacity-50 transition-colors px-3 py-1.5 rounded-lg text-xs font-black uppercase tracking-wider"
            >
              + Agregar
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <button
                onClick={onQuitar}
                disabled={isLoading}
                className="w-6 h-6 rounded-full border border-cine-line text-cine-cream hover:border-cine-crimson hover:text-cine-crimson transition-colors text-sm font-bold flex items-center justify-center"
              >
                −
              </button>
              <span className="font-mono text-cine-cream font-bold text-sm w-4 text-center">{cantidadEnCarrito}</span>
              <button
                onClick={onAgregar}
                disabled={isLoading}
                className="w-6 h-6 rounded-full bg-cine-gold text-cine-bg hover:bg-cine-gold/80 transition-colors text-sm font-bold flex items-center justify-center"
              >
                +
              </button>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

/* ─── Main Page ─── */
export function DulceriaPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const complejoSlug = useAppStore((s) => s.complejoSlug);
  const carritoId = useAppStore((s) => s.carritoId);
  const carritoFuncionId = useAppStore((s) => s.carritoFuncionId);

  const [productoSeleccionado, setProductoSeleccionado] = useState<ProductoDulceria | null>(null);
  const catRefs = useRef<Record<string, HTMLElement | null>>({});

  // Datos
  const { data: menuData, isLoading: isLoadingMenu } = useQuery({
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

  const mutAgregar = useMutation({
    mutationFn: (payload: any) => agregarProductoCarrito(carritoId!, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["carrito"] }),
  });
  const mutEliminar = useMutation({
    mutationFn: (detalleId: number) => eliminarItemCarrito(carritoId!, detalleId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["carrito"] }),
  });

  const categorias = menuData?.menu ?? [];

  // Cuántos de cada producto hay en el carrito (por producto_id)
  const cantidadesPorProducto = useMemo(() => {
    const map = new Map<number, number>();
    if (!carritoData?.items) return map;
    carritoData.items.forEach(item => {
      if (item.tipo_item === "producto" && item.producto_id != null) {
        map.set(item.producto_id, (map.get(item.producto_id) ?? 0) + item.cantidad);
      }
    });
    return map;
  }, [carritoData]);

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
    const grouped = new Map<number, { nombre: string; cantidad: number; precio: number; detalleIds: number[] }>();
    carritoData.items.forEach((i: any) => {
      if (i.tipo_item === "producto" && i.producto_id != null) {
        const prod = productosMap.get(i.producto_id) as any;
        if (grouped.has(i.producto_id)) {
          const g = grouped.get(i.producto_id)!;
          g.cantidad += i.cantidad;
          g.detalleIds.push(i.detalle_carrito_id);
        } else {
          grouped.set(i.producto_id, {
            nombre: prod?.nombre ?? `Producto ${i.producto_id}`,
            cantidad: i.cantidad,
            precio: Number(i.precio_unitario),
            detalleIds: [i.detalle_carrito_id],
          });
        }
      }
    });
    return Array.from(grouped.values());
  }, [carritoData, menuData]);

  const subtotalDulceria = productosEnCarrito.reduce((a, p) => a + p.precio * p.cantidad, 0);
  const subtotalBoletos = boletosEnCarrito.reduce((a, b) => a + b.precio, 0);
  const subtotal = subtotalBoletos + subtotalDulceria;

  const handleAgregarProducto = (prod: ProductoDulceria) => {
    if (prod.personalizacion && prod.personalizacion.length > 0) {
      setProductoSeleccionado(prod);
    } else {
      mutAgregar.mutate({
        producto_id: prod.producto_id,
        cantidad: 1,
        precio_unitario: prod.precio,
        personalizaciones: [],
      });
    }
  };

  const handleQuitarProducto = (prod: ProductoDulceria) => {
    // Find the last detalle_carrito_id for this product and remove it
    const items = carritoData?.items.filter((i: any) => i.tipo_item === "producto" && i.producto_id === prod.producto_id) ?? [];
    if (items.length > 0) {
      const last = items[items.length - 1];
      mutEliminar.mutate(last.detalle_carrito_id);
    }
  };

  const handlePersonalizacionConfirmada = (
    prod: ProductoDulceria,
    personalizaciones: { opcion_id: number; porcentaje: number; cantidad: number }[]
  ) => {
    mutAgregar.mutate({
      producto_id: prod.producto_id,
      cantidad: 1,
      precio_unitario: prod.precio,
      personalizaciones,
    });
    setProductoSeleccionado(null);
  };

  const scrollToCategoria = (nombre: string) => {
    catRefs.current[nombre]?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  if (!carritoId) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center text-cine-slate">
        <p className="font-display text-2xl mb-4">No tienes un carrito activo.</p>
        <button onClick={() => navigate("/")} className="text-cine-gold hover:underline">
          Volver a cartelera
        </button>
      </div>
    );
  }

  if (isLoadingMenu) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-cine-slate font-mono animate-pulse">Cargando dulcería…</p>
      </div>
    );
  }

  const posterFallback = mapaData
    ? `https://placehold.co/60x80/1a1d2e/c8a96a?text=${encodeURIComponent(mapaData.pelicula.slice(0, 2))}`
    : "";

  return (
    <>
      {/* Modal de Personalización */}
      {productoSeleccionado && (
        <ModalPersonalizacion
          producto={productoSeleccionado}
          onAgregar={(sel) => handlePersonalizacionConfirmada(productoSeleccionado, sel)}
          onCerrar={() => setProductoSeleccionado(null)}
        />
      )}

      <div className="max-w-7xl mx-auto px-4 py-8 grid lg:grid-cols-[1fr_320px] gap-8 items-start">
        {/* ── LEFT: Catálogo ── */}
        <div className="min-w-0">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-sm text-cine-slate mb-4 font-mono">
            <button onClick={() => navigate(-1)} className="hover:text-cine-gold transition-colors">← Asientos</button>
            <span className="text-cine-line">›</span>
            <span className="text-cine-cream font-bold">Dulcería</span>
            <span className="text-cine-line">›</span>
            <span>Pago</span>
          </div>

          <h1 className="font-display text-4xl tracking-wide leading-none mb-6">Dulcería</h1>

          {/* Category Tabs */}
          <div className="sticky top-0 z-10 bg-cine-bg/95 backdrop-blur-sm border-b border-cine-line pb-3 mb-8 pt-2">
            <div className="flex overflow-x-auto gap-2 hide-scrollbar">
              {categorias.map(cat => (
                <button
                  key={cat.categoria}
                  onClick={() => scrollToCategoria(cat.categoria)}
                  className="whitespace-nowrap px-4 py-2 rounded-full font-semibold text-xs transition-colors border bg-cine-bg-raised text-cine-slate border-cine-line hover:border-cine-gold hover:text-cine-cream flex-shrink-0"
                >
                  {cat.categoria}
                </button>
              ))}
            </div>
          </div>

          {/* Products by category */}
          <div className="space-y-12">
            {categorias.map(cat => (
              <section
                key={cat.categoria}
                ref={el => { catRefs.current[cat.categoria] = el; }}
                className="scroll-mt-24"
              >
                <h2 className="font-display text-2xl tracking-wide text-cine-cream mb-4">{cat.categoria}</h2>
                <div className="flex overflow-x-auto gap-4 pb-4 hide-scrollbar snap-x snap-mandatory">
                  {cat.productos.map(prod => (
                    <ProductoCard
                      key={prod.producto_id}
                      producto={prod}
                      cantidadEnCarrito={cantidadesPorProducto.get(prod.producto_id) ?? 0}
                      onAgregar={() => handleAgregarProducto(prod)}
                      onQuitar={() => handleQuitarProducto(prod)}
                      isLoading={mutAgregar.isPending || mutEliminar.isPending}
                    />
                  ))}
                </div>
              </section>
            ))}
          </div>
        </div>

        {/* ── RIGHT: Sidebar ── */}
        <aside className="lg:sticky lg:top-6 h-fit">
          <div className="bg-cine-bg-raised border border-cine-line rounded-xl overflow-hidden shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 bg-[#0a182b] border-b border-cine-line">
              <div className="flex items-center gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-cine-gold" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M3 1a1 1 0 000 2h1.22l.305 1.222a.997.997 0 00.01.042l1.358 5.43-.893.892C3.74 11.846 4.632 14 6.414 14H15a1 1 0 000-2H6.414l1-1H14a1 1 0 00.894-.553l3-6A1 1 0 0017 3H6.28l-.31-1.243A1 1 0 005 1H3zM16 16.5a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zM6.5 18a1.5 1.5 0 100-3 1.5 1.5 0 000 3z" />
                </svg>
                <span className="text-sm font-bold text-white uppercase tracking-wide">Tu carrito</span>
              </div>
              <span className="font-display text-lg text-white">${subtotal.toFixed(2)}</span>
            </div>

            {/* Movie info */}
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

            {/* Boletos */}
            <div className="px-4 py-3 border-b border-cine-line">
              <p className="text-[10px] text-cine-slate uppercase font-bold tracking-widest mb-2">
                Boletos ({boletosEnCarrito.length})
              </p>
              {boletosEnCarrito.length === 0 ? (
                <p className="text-xs text-cine-slate italic">Sin boletos</p>
              ) : (
                <div className="space-y-1.5">
                  {boletosEnCarrito.map((b, idx) => (
                    <div key={idx} className="flex justify-between text-xs">
                      <span className="text-cine-cream-dim">{b.tipo} · {b.etiqueta}</span>
                      <span className="font-mono text-cine-gold">${b.precio.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

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
                <div className="space-y-2">
                  {productosEnCarrito.map((p, idx) => (
                    <div key={idx} className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => {
                              const item = carritoData?.items.find((i: any) => i.tipo_item === "producto" && i.producto_id === (carritoData?.items.filter((x: any) => x.tipo_item === "producto")[idx]?.producto_id));
                              if (item) mutEliminar.mutate(item.detalle_carrito_id);
                            }}
                            className="w-5 h-5 rounded-full border border-cine-line text-cine-slate hover:border-cine-crimson hover:text-cine-crimson transition-colors text-xs flex items-center justify-center"
                          >−</button>
                          <span className="font-mono text-cine-cream text-xs font-bold w-4 text-center">{p.cantidad}</span>
                        </div>
                        <span className="text-cine-cream-dim text-xs line-clamp-1">{p.nombre}</span>
                      </div>
                      <span className="font-mono text-cine-gold text-xs flex-shrink-0">${(p.precio * p.cantidad).toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Subtotal y CTA */}
            <div className="p-4">
              <div className="flex justify-between text-sm mb-4">
                <span className="text-cine-slate">Subtotal</span>
                <span className="font-display text-lg text-cine-gold">${subtotal.toFixed(2)}</span>
              </div>
              <button
                onClick={() => navigate("/checkout")}
                disabled={boletosEnCarrito.length === 0}
                className="w-full bg-[#e31837] hover:bg-[#c41530] disabled:opacity-40 disabled:cursor-not-allowed transition-colors rounded-xl py-3.5 font-bold tracking-wide text-white text-sm shadow-md"
              >
                Proceder al pago
              </button>
              <button
                onClick={() => navigate("/checkout")}
                className="w-full mt-2 text-cine-slate hover:text-cine-cream text-xs py-2 transition-colors"
              >
                Omitir dulcería →
              </button>
            </div>
          </div>
        </aside>
      </div>
    </>
  );
}
