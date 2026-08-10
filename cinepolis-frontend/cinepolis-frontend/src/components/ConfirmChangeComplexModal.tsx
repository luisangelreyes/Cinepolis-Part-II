interface ConfirmChangeComplexModalProps {
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmChangeComplexModal({ isOpen, onConfirm, onCancel }: ConfirmChangeComplexModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onCancel}
      />
      
      {/* Modal */}
      <div className="relative bg-white text-[#0a182b] rounded-3xl p-8 max-w-lg w-full text-center shadow-2xl transform transition-all">
        <h2 className="text-2xl sm:text-3xl font-bold mb-4">
          ¿Estás seguro de comenzar una nueva orden?
        </h2>
        
        <p className="text-gray-500 font-medium mb-8">
          Perderás los artículos que se encuentran en tu carrito
        </p>

        <div className="flex flex-col gap-3">
          <button
            onClick={onConfirm}
            className="w-full bg-[#4a81f5] hover:bg-[#3b6dd8] text-white font-bold py-3.5 rounded-xl transition-colors"
          >
            Aceptar
          </button>
          <button
            onClick={onCancel}
            className="w-full bg-white hover:bg-gray-50 text-[#0a182b] font-bold py-3.5 rounded-xl border border-gray-300 transition-colors"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
}
