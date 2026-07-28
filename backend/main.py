from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from controllers.marketing import router as marketing_router
from controllers.system import router as system_router
from controllers.movies import router as movies_router
from controllers.cart import router as cart_router
from controllers.dulceria import router as dulceria_router
from controllers.club import router as club_router
from controllers.staff import router as staff_router
from controllers.claims import router as claims_router

# =================================================================
# INICIALIZACIÓN DE LA APP
# =================================================================
app = FastAPI(
    title="Cinépolis - Proyecto Vision API (Refactored MVC)",
    description="Backend central para la gestión de Cartelera, Dulcería y Transacciones. Refactorizado a MVC.",
    version="1.1.0"
)

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =================================================================
# REGISTRO DE RUTAS
# =================================================================
app.include_router(system_router)
app.include_router(marketing_router)
app.include_router(movies_router)
app.include_router(cart_router)
app.include_router(dulceria_router)
app.include_router(club_router)
app.include_router(staff_router)
app.include_router(claims_router)