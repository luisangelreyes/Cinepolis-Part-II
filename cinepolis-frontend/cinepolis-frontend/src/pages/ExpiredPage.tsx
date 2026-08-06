import { useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { useAppStore } from "../store/useAppStore";

export function ExpiredPage() {
  const navigate = useNavigate();
  const setCarritoId = useAppStore(s => s.setCarritoId);

  // Garantizar que la sesión esté limpia si llega aquí por accidente
  useEffect(() => {
    setCarritoId(null);
  }, [setCarritoId]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4 bg-white text-[#0b162c] absolute inset-0 z-50">
      <h1 className="text-5xl md:text-6xl font-extrabold mb-4 tracking-tight font-display">Tu sesión expiró</h1>
      <p className="text-gray-500 mb-12 text-lg font-body">Lo sentimos, pero tu sesión ha terminado.</p>
      
      <p className="text-gray-500 text-sm mb-6 font-body">Puedes comenzar nuevamente, dando clic en el siguiente botón.</p>
      
      <button
        onClick={() => navigate("/", { replace: true })}
        className="bg-[#3e7af0] hover:bg-[#3263c9] text-white font-bold py-4 px-12 rounded-xl transition-colors text-lg shadow-lg shadow-blue-500/30 font-body"
      >
        Ir al Inicio
      </button>
    </div>
  );
}
