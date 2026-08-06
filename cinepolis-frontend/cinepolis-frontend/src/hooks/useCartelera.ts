import { useQuery } from "@tanstack/react-query";
import { getCartelera, getFechasCartelera } from "../api/endpoints";

export function useCartelera(complejoSlug: string, fecha: string) {
  return useQuery({
    queryKey: ["cartelera", complejoSlug, fecha],
    queryFn: () => getCartelera(complejoSlug, fecha),
    enabled: Boolean(complejoSlug && fecha),
    staleTime: 60_000,
  });
}

export function useFechasCartelera(complejoSlug: string) {
  return useQuery({
    queryKey: ["fechas", complejoSlug],
    queryFn: () => getFechasCartelera(complejoSlug),
    enabled: Boolean(complejoSlug),
    staleTime: 60_000,
  });
}
