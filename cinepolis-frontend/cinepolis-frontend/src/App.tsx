import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CarteleraPage } from "./pages/CarteleraPage";
import { SeatSelectionPage } from "./pages/SeatSelectionPage";

const queryClient = new QueryClient();

function CarritoPlaceholder() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-16 text-center">
      <p className="font-display text-4xl tracking-wide mb-2">Dulcería y pago</p>
      <p className="text-cine-slate">
        Este módulo (carrito de dulcería + checkout) va en la siguiente iteración.
      </p>
    </div>
  );
}

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <div className="film-grain" />
      <header className="border-b border-cine-line">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="font-display text-2xl tracking-widest text-cine-gold">
            CINÉPOLIS · SECRET WARS
          </Link>
          <span className="text-xs text-cine-slate font-mono hidden sm:block">
            Veracruz, México
          </span>
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
            <Route path="/carrito" element={<CarritoPlaceholder />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
