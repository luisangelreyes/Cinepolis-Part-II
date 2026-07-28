import { useQuery } from "@tanstack/react-query";
import { getPelicula } from "../api/endpoints";

export function usePelicula(peliculaId: number | null) {
  return useQuery({
    queryKey: ["pelicula", peliculaId],
    queryFn: () => getPelicula(peliculaId!),
    enabled: peliculaId !== null,
    staleTime: 5 * 60_000,
  });
}
