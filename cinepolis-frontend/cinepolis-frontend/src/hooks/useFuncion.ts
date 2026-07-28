import { useQuery } from "@tanstack/react-query";
import { getAsientosPorFuncion, getPreciosPorFuncion } from "../api/endpoints";

export function useAsientosFuncion(funcionId: number) {
  return useQuery({
    queryKey: ["asientos", funcionId],
    queryFn: () => getAsientosPorFuncion(funcionId),
    enabled: Boolean(funcionId),
  });
}

export function usePreciosFuncion(funcionId: number) {
  return useQuery({
    queryKey: ["precios", funcionId],
    queryFn: () => getPreciosPorFuncion(funcionId),
    enabled: Boolean(funcionId),
  });
}
