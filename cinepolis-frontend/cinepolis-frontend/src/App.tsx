import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CarteleraPage } from "./pages/CarteleraPage";
import { SeatSelectionPage } from "./pages/SeatSelectionPage";

const queryClient = new QueryClient();

import { DulceriaPage } from "./pages/DulceriaPage";

import { CartTimer } from "./components/CartTimer";
import { ExpiredPage } from "./pages/ExpiredPage";
import { CheckoutPage } from "./pages/CheckoutPage";
import { TicketPage } from "./pages/TicketPage";
import { AlimentosPage } from "./pages/AlimentosPage";
import { useAppStore } from "./store/useAppStore";
import { useQuery } from "@tanstack/react-query";
import { getCarrito } from "./api/endpoints";
import { CartSummary } from "./components/CartSummary";

function CartButton() {
  const carritoId = useAppStore(s => s.carritoId);
  const setIsCartOpen = useAppStore(s => s.setIsCartOpen);

  const { data: carritoData } = useQuery({
    queryKey: ["carrito", carritoId],
    queryFn: () => getCarrito(carritoId!),
    enabled: !!carritoId,
  });

  if (!carritoId) return null;

  const totalItems = carritoData?.items?.reduce((acc: number, item: any) => acc + item.cantidad, 0) || 0;

  return (
    <button 
      onClick={() => setIsCartOpen(true)}
      className="relative p-2 text-cine-cream hover:text-cine-gold transition-colors ml-4"
    >
      <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
      {totalItems > 0 && (
        <span className="absolute top-0 right-0 bg-[#e31837] text-white text-[10px] font-bold h-4 w-4 rounded-full flex items-center justify-center transform translate-x-1 -translate-y-1">
          {totalItems}
        </span>
      )}
    </button>
  );
}

function CartDrawer() {
  const isCartOpen = useAppStore(s => s.isCartOpen);
  const setIsCartOpen = useAppStore(s => s.setIsCartOpen);
  const carritoId = useAppStore(s => s.carritoId);

  if (!carritoId) return null;

  return (
    <>
      {isCartOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity"
          onClick={() => setIsCartOpen(false)}
        />
      )}
      <div 
        className={`fixed top-0 right-0 h-full w-full sm:w-[400px] z-50 transform transition-transform duration-300 ease-in-out ${isCartOpen ? 'translate-x-0' : 'translate-x-full'}`}
      >
        <div className="h-full bg-cine-bg shadow-2xl overflow-hidden flex flex-col p-4 pt-6 sm:p-6">
          <CartSummary onClose={() => setIsCartOpen(false)} />
        </div>
      </div>
    </>
  );
}

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <CartTimer />
      <CartDrawer />
      <div className="film-grain" />
      <header className="border-b border-cine-line">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link to="/" className="font-display text-2xl tracking-widest text-cine-gold">
              CINÉPOLIS · SECRET WARS
            </Link>
            <nav className="hidden sm:flex gap-6">
              <Link to="/alimentos" className="text-sm font-bold text-cine-cream hover:text-cine-gold transition-colors tracking-wide">
                Alimentos
              </Link>
            </nav>
          </div>
          <div className="flex items-center">
            <span className="text-xs text-cine-slate font-mono hidden sm:block">
              Veracruz, México
            </span>
            <CartButton />
          </div>
        </div>
      </header>
      <main>{children}</main>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<CarteleraPage />} />
            <Route path="/funcion/:funcionId/asientos" element={<SeatSelectionPage />} />
            <Route path="/carrito" element={<DulceriaPage />} />
            <Route path="/alimentos" element={<AlimentosPage />} />
            <Route path="/checkout" element={<CheckoutPage />} />
            <Route path="/ticket" element={<TicketPage />} />
            <Route path="/expired" element={<ExpiredPage />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
