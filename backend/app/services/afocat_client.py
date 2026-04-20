"""
AFOCAT Piura API Client — integrates with syserp.afocatpiura.com
for CAT (Certificado contra Accidentes de Transito) sales.

Handles: login, DNI lookup, plate lookup, sell CAT, search CAT.
"""

import logging
from datetime import datetime, timezone

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

AFOCAT_BASE = "https://syserp.afocatpiura.com"


class AfocatClient:
    """Session-based client for AFOCAT Piura API."""

    def __init__(self):
        self._client = httpx.Client(base_url=AFOCAT_BASE, timeout=15, follow_redirects=True)
        self._logged_in = False

    def _ensure_login(self):
        """Login if not already authenticated."""
        if self._logged_in:
            return

        user = settings.AFOCAT_USER
        password = settings.AFOCAT_PASS

        if not user or not password:
            raise ValueError("AFOCAT credentials not configured (AFOCAT_USER, AFOCAT_PASS)")

        resp = self._client.post("/api/login", data={"email": user, "pass": password})
        data = resp.json()

        if data.get("success") != 1:
            self._logged_in = False
            raise ValueError(f"AFOCAT login failed: {data.get('message', 'Unknown error')}")

        self._logged_in = True
        logger.info("AFOCAT: logged in successfully")

    def lookup_dni(self, dni: str) -> dict:
        """Lookup customer by DNI."""
        self._ensure_login()
        resp = self._client.post("/api/DNI", data={"nro_documento": dni})
        data = resp.json()

        if data.get("success") != 1:
            return {"found": False, "error": data.get("message", "Not found")}

        return {
            "found": True,
            "ap_paterno": data.get("ap_paterno", ""),
            "ap_materno": data.get("ap_materno", ""),
            "nombre": data.get("nom_razon", ""),
            "full_name": f"{data.get('ap_paterno', '')} {data.get('ap_materno', '')} {data.get('nom_razon', '')}".strip(),
            "telefono": data.get("telefono", ""),
            "direccion": data.get("direccion", ""),
            "nacionalidad": data.get("nacionalidad", ""),
            "ambito": data.get("ambito", 0),
            "ubigeo": data.get("ubigeo", 0),
        }

    def lookup_placa(self, placa: str) -> dict:
        """Lookup vehicle by license plate."""
        self._ensure_login()
        resp = self._client.post("/api/PLACA", data={"placa": placa.upper()})
        data = resp.json()

        if data.get("success") != 1:
            return {"found": False, "error": data.get("message", "Not found")}

        v = data.get("vehiculo", {})
        return {
            "found": True,
            "placa": v.get("placa", ""),
            "año": v.get("año"),
            "marca": v.get("marca", ""),
            "modelo": v.get("modelo", ""),
            "asientos": v.get("asientos"),
            "serie": v.get("serie", ""),
            "categoria": v.get("categoria", ""),
            "clase": v.get("clase", ""),
            "uso": v.get("uso", ""),
            "precio": v.get("precio", 0),
            "ap_extra": v.get("ap_extra", 0),
            "precio_total": (v.get("precio", 0) or 0) + (v.get("ap_extra", 0) or 0),
            "vigencia_dias": v.get("vigencia", 0),
            "vigente": (v.get("vigencia", 0) or 0) > 0,
            "n_tecnica": v.get("n_tecnica"),
        }

    def get_pending_cats(self) -> list[dict]:
        """Get pending CAT certificates for this sales point."""
        self._ensure_login()
        resp = self._client.post("/api/_V_Cat_Pendientes")
        data = resp.json()
        return data.get("Cat_Liq", [])

    def sell_cat(self, form_data: dict) -> dict:
        """
        Sell a CAT certificate.

        form_data should match the fields the AFOCAT system expects.
        Returns the response including PDF paths and certificate number.
        """
        self._ensure_login()
        resp = self._client.post("/api/Cat_vender", data=form_data)

        if resp.status_code != 200:
            return {"success": False, "error": f"HTTP {resp.status_code}"}

        try:
            data = resp.json()
            return {
                "success": data.get("success") == 1,
                "message": data.get("message", ""),
                "pdf_cat": data.get("pdf_cat"),
                "pdf_cpe": data.get("pdf_cpe"),
                "raw": data,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_cat(self, search_data: dict) -> dict:
        """Search for an existing CAT certificate."""
        self._ensure_login()
        resp = self._client.post("/api/_Search_Cat", data=search_data)
        data = resp.json()
        return data

    def close(self):
        """Close the HTTP client."""
        self._client.close()


# Singleton instance
_client: AfocatClient | None = None


def get_afocat_client() -> AfocatClient:
    """Get or create the singleton AFOCAT client."""
    global _client
    if _client is None:
        _client = AfocatClient()
    return _client
