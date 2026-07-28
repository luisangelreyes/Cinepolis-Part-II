from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

class CrearCarritoRequest(BaseModel):
    sesion_id: Optional[int] = None   
    socio_id: Optional[int] = None    

class AgregarAsientoRequest(BaseModel):
    asiento_id: int
    tipo_boleto_id: int          
    precio_unitario: float

class ItemPersonalizacion(BaseModel):
    opcion_id: int
    porcentaje: Optional[int] = None  
    cantidad: Optional[int] = None    

class AgregarProductoRequest(BaseModel):
    producto_id: int
    cantidad: int = 1
    precio_unitario: float
    personalizaciones: List[ItemPersonalizacion] = Field(default_factory=list)

class PagarCarritoRequest(BaseModel):
    forma_pago: str          
    tipo_venta: str = "Online"
    sesion_id: Optional[int] = None   
    nombre_comprador: Optional[str] = None
    apellido_comprador: Optional[str] = None
    correo_comprador: Optional[str] = None
    cargo_servicio_por_boleto: float = 6.0

class SolicitarOTPRequest(BaseModel):
    correo: str

class VerificarOTPRequest(BaseModel):
    correo: str
    codigo: str
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    genero: Optional[str] = None       
    codigo_postal: Optional[str] = None

class CanjearPuntosRequest(BaseModel):
    cantidad_puntos: float

class PersonalLoginRequest(BaseModel):
    empleado_id: int  

class AbrirSesionRequest(BaseModel):
    empleado_id: int      
    caja_id: int
    saldo_inicial: float

class CerrarSesionRequest(BaseModel):
    saldo_reportado_efectivo: float
    notas: Optional[str] = None

class CrearReclamoRequest(BaseModel):
    nombre_reclamante: str
    correo: str
    motivo: str
    pelicula_id: int
    complejo_id: int
    venta_id: Optional[int] = None

class GarantiaReclamoRequest(BaseModel):
    nombre_reclamante: str
    correo: str
    motivo: str
    pelicula_id: int
    complejo_id: int
    venta_id: Optional[int] = None
