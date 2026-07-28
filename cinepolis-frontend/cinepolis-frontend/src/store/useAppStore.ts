import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AppState {
  complejoSlug: string;
  carritoId: number | null;
  socioId: number | null;
  setComplejoSlug: (slug: string) => void;
  setCarritoId: (id: number | null) => void;
  setSocioId: (id: number | null) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // El Dorado Veracruz por default (complejo_id 19 según tus notas de Vision)
      complejoSlug: "cinepolis-el-dorado-veracruz",
      carritoId: null,
      socioId: null,
      setComplejoSlug: (slug) => set({ complejoSlug: slug }),
      setCarritoId: (id) => set({ carritoId: id }),
      setSocioId: (id) => set({ socioId: id }),
    }),
    { name: "cinepolis-app-store" }
  )
);
