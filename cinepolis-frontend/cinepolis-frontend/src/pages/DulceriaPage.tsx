import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAppStore } from "../store/useAppStore";
import { getDulceria, getCarrito, agregarProductoCarrito, eliminarItemCarrito } from "../api/endpoints";
import type { ProductoDulceria } from "../types/api";

export function DulceriaPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const complejoSlug = useAppStore((s) => s.complejoSlug);
  const carritoId = useAppStore((s) => s.carritoId);

  const [productoSeleccionado, setProductoSeleccionado] = useState<ProductoDulceria | null>(null);

  // Consultar menú
  const { data: menuData, isLoading: isLoadingMenu } = useQuery({
    queryKey: ["dulceria", complejoSlug],
    queryFn: () => getDulceria(complejoSlug),
  });

  // Consultar carrito
  const { data: carritoData } = useQuery({
    queryKey: ["carrito", carritoId],
    queryFn: () => getCarrito(carritoId!),
    enabled: !!carritoId,
  });

  // Mutaciones
  const mutAgregar = useMutation({
    mutationFn: (payload: any) => agregarProductoCarrito(carritoId!, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["carrito"] }),
  });

  const mutEliminar = useMutation({
    mutationFn: (detalleId: number) => eliminarItemCarrito(carritoId!, detalleId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["carrito"] }),
  });

  const categorias = menuData?.menu ?? [];

  const handleAgregarDirecto = (producto: ProductoDulceria) => {
    if (producto.personalizacion && producto.personalizacion.length > 0) {
      setProductoSeleccionado(producto);
    } else {
      mutAgregar.mutate({
        producto_id: producto.producto_id,
        cantidad: 1,
        precio_unitario: producto.precio,
        personalizaciones: [],
      });
    }
  };

  const calcularSubtotal = () => {
    if (!carritoData?.items) return 0;
    return carritoData.items.reduce((acc, item) => acc + item.cantidad * Number(item.precio_unitario), 0);
  };

  const groupedItems = useMemo(() => {
    if (!carritoData?.items) return [];
    const result: any[] = [];
    
    // Create a flat map of all products to easily look up names
    const productMap = new Map<number, string>();
    categorias.forEach(cat => {
      cat.productos.forEach(p => {
        productMap.set(p.producto_id, p.nombre);
      });
    });

    const productGroups = new Map<number, any>();

    carritoData.items.forEach(item => {
      if (item.tipo_item === "boleto") {
        result.push({
          ...item,
          isGrouped: false,
          displayName: "Boleto",
          idsToRemove: [item.detalle_carrito_id]
        });
      } else if (item.tipo_item === "producto" && item.producto_id) {
        if (productGroups.has(item.producto_id)) {
          const group = productGroups.get(item.producto_id);
          group.cantidad += item.cantidad;
          group.idsToRemove.push(item.detalle_carrito_id);
        } else {
          const newGroup = {
            ...item,
            isGrouped: true,
            displayName: productMap.get(item.producto_id) || "Producto",
            idsToRemove: [item.detalle_carrito_id]
          };
          productGroups.set(item.producto_id, newGroup);
          result.push(newGroup);
        }
      }
    });

    return result;
  }, [carritoData?.items, categorias]);

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
    return <div className="max-w-6xl mx-auto px-4 py-10 text-cine-slate font-mono">Cargando dulcería...</div>;
  }

  const scrollToCategoria = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 grid lg:grid-cols-[1fr_340px] gap-8 items-start">
      {/* Panel Izquierdo: Menú Completo */}
      <div className="min-w-0">
        <div className="flex items-center justify-between mb-6">
          <h1 className="font-display text-4xl tracking-wide leading-none">Dulcería</h1>
        </div>
        
        {/* Enlaces Rápidos de Categorías */}
        <div className="sticky top-0 z-10 bg-cine-bg/95 backdrop-blur-sm border-b border-cine-line pb-4 mb-8 pt-2">
          <div className="flex overflow-x-auto gap-2 hide-scrollbar">
            {categorias.map((cat) => (
              <button
                key={cat.categoria}
                onClick={() => scrollToCategoria(`cat-${cat.categoria}`)}
                className="whitespace-nowrap px-4 py-2 rounded-full font-semibold text-sm transition-colors border bg-cine-bg-raised text-cine-slate border-cine-line hover:border-cine-gold hover:text-cine-cream"
              >
                {cat.categoria}
              </button>
            ))}
          </div>
        </div>

        {/* Listado Vertical de Categorías con Scroll Horizontal Interno */}
        <div className="space-y-12">
          {categorias.map((cat) => (
            <section key={cat.categoria} id={`cat-${cat.categoria}`} className="scroll-mt-24">
              <h2 className="font-display text-2xl tracking-wide text-cine-cream mb-4">{cat.categoria}</h2>
              
              <div className="flex overflow-x-auto gap-5 pb-4 hide-scrollbar snap-x">
                {cat.productos.map((prod) => (
                  <article 
                    key={prod.producto_id} 
                    className="w-[220px] sm:w-[260px] shrink-0 bg-cine-bg-raised border border-cine-line rounded-xl overflow-hidden flex flex-col hover:border-cine-gold/50 transition-colors snap-start"
                  >
                    <div className="aspect-[4/3] bg-cine-line/30 relative">
                      {prod.imagen_url ? (
                        <img src={prod.imagen_url} alt={prod.nombre} className="w-full h-full object-cover" loading="lazy" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-cine-slate text-xs">Sin imagen</div>
                      )}
                    </div>
                    <div className="p-4 flex flex-col flex-1">
                      <h3 className="font-bold text-cine-cream text-base leading-tight mb-2">{prod.nombre}</h3>
                      <p className="text-cine-slate text-[11px] mb-4 line-clamp-3 flex-1">{prod.descripcion}</p>
                      
                      <div className="flex items-center justify-between mt-auto pt-2 border-t border-cine-line/50">
                        <span className="font-mono text-lg text-cine-gold font-semibold">${prod.precio.toFixed(2)}</span>
                        <button
                          onClick={() => handleAgregarDirecto(prod)}
                          disabled={mutAgregar.isPending}
                          className="bg-cine-gold text-cine-bg hover:bg-[#e5b33e] disabled:opacity-50 transition-colors px-4 py-1.5 rounded text-xs font-bold uppercase tracking-wider"
                        >
                          Agregar
                        </button>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>

      {/* Panel Derecho: Carrito Rediseñado */}
      <aside className="bg-cine-bg border border-cine-line rounded-2xl overflow-hidden h-fit lg:sticky lg:top-24 flex flex-col max-h-[80vh] shadow-xl">
        <div className="bg-[#0b162c] px-5 py-4 border-b border-cine-line/30">
          <h2 className="font-display text-xl tracking-wide text-white flex items-center gap-2">
            <svg className="w-5 h-5 text-cine-gold" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            Tu Carrito
          </h2>
        </div>
        
        <div className="flex-1 overflow-y-auto p-5 space-y-4 custom-scrollbar bg-cine-bg-raised">
          {groupedItems.length === 0 && (
            <p className="text-cine-slate text-sm text-center py-4">No has agregado elementos a tu orden.</p>
          )}
          
          {groupedItems.map((item) => (
            <div key={item.isGrouped ? `prod-${item.producto_id}` : `bol-${item.detalle_carrito_id}`} className="flex justify-between items-start text-sm bg-cine-bg p-3 rounded-lg border border-cine-line/50">
              <div className="flex-1 pr-2">
                <span className="text-cine-cream font-medium block">
                  {item.cantidad}x {item.displayName}
                </span>
                <span className="text-cine-slate text-xs font-mono">
                  ${Number(item.precio_unitario).toFixed(2)} c/u
                </span>
              </div>
              <div className="flex flex-col items-end gap-2">
                <span className="text-cine-cream-dim font-mono font-semibold">${(Number(item.precio_unitario) * item.cantidad).toFixed(2)}</span>
                <button
                  onClick={() => mutEliminar.mutate(item.idsToRemove[item.idsToRemove.length - 1])}
                  disabled={mutEliminar.isPending}
                  className="text-cine-crimson/80 hover:text-cine-crimson text-[10px] uppercase font-bold tracking-wider"
                >
                  Quitar
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="bg-cine-bg p-5 border-t border-cine-line">
          <div className="flex justify-between items-baseline mb-4">
            <span className="text-cine-slate text-sm uppercase tracking-wide font-semibold">Total a pagar</span>
            <span className="font-display text-3xl text-cine-gold">${calcularSubtotal().toFixed(2)}</span>
          </div>

          <button
            disabled={!carritoData?.items || carritoData.items.length === 0}
            onClick={() => navigate("/checkout")}
            className="w-full bg-[#e31837] hover:bg-[#c41530] disabled:opacity-40 disabled:cursor-not-allowed transition-colors rounded-xl py-3.5 font-body font-bold tracking-wide text-white text-sm shadow-md"
          >
            Proceder al pago
          </button>
        </div>
      </aside>

      {/* Modal de Personalización Básico */}
      {productoSeleccionado && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-cine-bg border border-cine-line rounded-2xl w-full max-w-lg p-6 shadow-2xl relative">
            <h2 className="text-2xl font-bold text-cine-cream mb-2">Personaliza tu {productoSeleccionado.nombre}</h2>
            <p className="text-cine-slate text-sm mb-6">Selecciona los sabores o modificadores para este producto.</p>
            
            <p className="text-cine-gold mb-6 font-mono text-sm">(El UI de modificadores interactivo vendrá luego. Por ahora se añadirá de forma básica).</p>
            
            <div className="flex gap-3 mt-8">
              <button
                onClick={() => {
                  mutAgregar.mutate({
                    producto_id: productoSeleccionado.producto_id,
                    cantidad: 1,
                    precio_unitario: productoSeleccionado.precio,
                    personalizaciones: [],
                  });
                  setProductoSeleccionado(null);
                }}
                className="flex-1 bg-cine-gold text-cine-bg font-bold py-3 rounded-lg hover:bg-cine-gold/90 transition-colors"
              >
                Agregar
              </button>
              <button
                onClick={() => setProductoSeleccionado(null)}
                className="flex-1 bg-cine-bg-raised text-cine-slate border border-cine-line font-bold py-3 rounded-lg hover:text-cine-cream transition-colors"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
