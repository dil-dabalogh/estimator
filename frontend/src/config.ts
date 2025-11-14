export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ""
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || (
  typeof window !== "undefined" && window.location.protocol === "https:" 
    ? "wss://" + window.location.host 
    : "ws://" + (window.location?.host || "localhost:5173")
)

