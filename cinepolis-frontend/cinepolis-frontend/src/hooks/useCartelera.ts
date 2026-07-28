import { useQuery } from "@tanstack/react-query";
import { getCartelera } from "../api/endpoints";

export function useCartelera(complejoSlug: string, fecha: string) {
  return useQuery({
    queryKey: ["cartelera", complejoSlug, fecha],
    queryFn: () => getCartelera(complejoSlug, fecha),
    enabled: Boolean(complejoSlug && fecha),
    staleTime: 60_000,
  });
}
