import axios from "axios";

// Cambia esto si tu backend corre en otro host/puerto.
// En desarrollo local uvicorn suele levantar en el 8000.
export const API_BASE_URL = "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Interceptor simple para que los errores de FastAPI (detail: "...")
// lleguen como Error legible en los componentes.
api.interceptors.response.use(
  (res) => res,
  (error) => {
    const detail = error?.response?.data?.detail;
    return Promise.reject(new Error(detail || error.message || "Error de red"));
  }
);
