import { useState, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAppStore } from "../store/useAppStore";
import { getDulceria, getCarrito, agregarProductoCarrito, eliminarItemCarrito } from "../api/endpoints";
import type { ProductoDulceria } from "../types/api";
import { ModalPersonalizacion } from "../components/ModalPersonalizacion";
import { CartSummary } from "../components/CartSummary";


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
    personalizaciones: { opcion_id: number; porcentaje?: number; cantidad: number }[],
    precioFinal: number
  ) => {
    mutAgregar.mutate({
      producto_id: prod.producto_id,
      cantidad: 1,
      precio_unitario: precioFinal,
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


  return (
    <>
      {/* Modal de Personalización */}
      {productoSeleccionado && (
        <ModalPersonalizacion
          producto={productoSeleccionado}
          onAgregar={(sel, precioFinal) => handlePersonalizacionConfirmada(productoSeleccionado, sel, precioFinal)}
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
        <aside className="lg:sticky lg:top-6 h-[calc(100vh-6rem)]">
          <CartSummary />
        </aside>
      </div>
    </>
  );
}
