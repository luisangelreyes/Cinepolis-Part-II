import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AppState {
  complejoSlug: string;
  carritoId: number | null;
  carritoFuncionId: number | null;
  carritoModoAlimentos: boolean;
  isCartOpen: boolean;
  socioId: number | null;
  setComplejoSlug: (slug: string) => void;
  setCarritoId: (id: number | null, funcionId?: number | null) => void;
  setCarritoModoAlimentos: (modo: boolean) => void;
  setIsCartOpen: (open: boolean) => void;
  setSocioId: (id: number | null) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // El Dorado Veracruz por default (complejo_id 19 según tus notas de Vision)
      complejoSlug: "cinepolis-el-dorado-veracruz",
      carritoId: null,
      carritoFuncionId: null,
      carritoModoAlimentos: false,
      isCartOpen: false,
      socioId: null,
      setComplejoSlug: (slug) => set((state) => {
        if (state.complejoSlug !== slug) {
          return { 
            complejoSlug: slug, 
            carritoId: null, 
            carritoFuncionId: null, 
            carritoModoAlimentos: false 
          };
        }
        return { complejoSlug: slug };
      }),
      setCarritoId: (id, funcionId) => set({ carritoId: id, carritoFuncionId: funcionId ?? null }),
      setCarritoModoAlimentos: (modo) => set({ carritoModoAlimentos: modo }),
      setIsCartOpen: (open) => set({ isCartOpen: open }),
      setSocioId: (id) => set({ socioId: id }),
    }),
    { name: "cinepolis-app-store" }
  )
);
