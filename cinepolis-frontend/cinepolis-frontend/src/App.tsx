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

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <CartTimer />
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
            <Route path="/carrito" element={<DulceriaPage />} />
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
