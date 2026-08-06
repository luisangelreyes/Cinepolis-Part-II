import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAppStore } from '../store/useAppStore';
import { useNavigate } from 'react-router-dom';
import { extenderCarrito } from '../api/endpoints';
import type { CarritoResponse } from '../types/api';

export function CartTimer() {
  const carritoId = useAppStore((s) => s.carritoId);
  const setCarritoId = useAppStore((s) => s.setCarritoId);
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [timeLeft, setTimeLeft] = useState<number | null>(null);
  const [showWarning, setShowWarning] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [extending, setExtending] = useState(false);

  // Reset dismissed state when cart changes
  useEffect(() => {
    setDismissed(false);
  }, [carritoId]);

  useEffect(() => {
    if (!carritoId) {
      setTimeLeft(null);
      setShowWarning(false);
      return;
    }

    const interval = setInterval(() => {
      const cached = queryClient.getQueryData<CarritoResponse>(['carrito', carritoId]);
      if (cached?.fecha_expiracion) {
        const exp = new Date(cached.fecha_expiracion).getTime();
        const now = new Date().getTime();
        const remaining = Math.max(0, Math.floor((exp - now) / 1000));
        
        setTimeLeft(remaining);

        if (remaining <= 0) {
          // Expired
          setCarritoId(null);
          navigate('/expired', { replace: true });
        } else if (remaining <= 300 && !dismissed) {
          // 5 minutes warning
          setShowWarning(true);
        } else {
          setShowWarning(false);
        }
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [carritoId, queryClient, navigate, setCarritoId, dismissed]);

  if (!showWarning || timeLeft === null) return null;

  const minutes = Math.floor(timeLeft / 60);
  const seconds = timeLeft % 60;
  const timeString = `${minutes}:${seconds.toString().padStart(2, '0')}`;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-white rounded-3xl w-full max-w-lg p-8 shadow-2xl flex flex-col items-center text-center animate-in fade-in zoom-in-95 duration-200">
        <h2 className="text-[#0b162c] text-3xl font-extrabold mb-3 font-body">Hola, amig@, ¿hay alguien en casa?</h2>
        <p className="text-gray-500 text-sm mb-6 font-body">¿Sigues ahí? El tiempo para realizar tu compra está por agotarse.</p>
        
        <p className="text-[#e31837] text-4xl font-black mb-8 font-mono tracking-widest">{timeString}</p>

        <button
          disabled={extending}
          onClick={async () => {
            setExtending(true);
            try {
              if (carritoId) {
                await extenderCarrito(carritoId);
                await queryClient.invalidateQueries({ queryKey: ["carrito", carritoId] });
              }
              setShowWarning(false);
              setDismissed(true);
            } catch (error) {
              console.error("No se pudo extender el carrito", error);
              alert("Error de conexión. Intenta pagar rápido antes de que expire el carrito.");
              setShowWarning(false);
              setDismissed(true);
            } finally {
              setExtending(false);
            }
          }}
          className="bg-[#3e7af0] hover:bg-[#3263c9] disabled:opacity-50 text-white font-bold py-4 px-8 rounded-xl w-full max-w-sm transition-colors text-lg shadow-lg shadow-blue-500/30 font-body"
        >
          {extending ? "Extendiendo tiempo..." : "Continuar compra"}
        </button>
      </div>
    </div>
  );
}
