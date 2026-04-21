"""
AFOCAT Piura API Client — integrates with syserp.afocatpiura.com
for CAT (Certificado contra Accidentes de Transito) sales.

Endpoints use "Test_" prefix (that's their production naming).
Flow: login → lookup plate → lookup DNI → get cert number → sell → get PDF
"""

import logging

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

    def _post(self, endpoint: str, data: dict | list | None = None) -> dict:
        """POST to AFOCAT API with auto-login and retry on session expiry."""
        self._ensure_login()
        resp = self._client.post(f"/api/{endpoint}", data=data)

        # If session expired, re-login and retry
        if resp.status_code == 302 or (resp.status_code == 200 and "login" in resp.text[:200].lower()):
            self._logged_in = False
            self._ensure_login()
            resp = self._client.post(f"/api/{endpoint}", data=data)

        return resp.json()

    def lookup_dni(self, dni: str) -> dict:
        """Lookup customer by DNI."""
        try:
            data = self._post("Test_Cat_DNI", {"nro_documento": dni})
        except Exception:
            # Fallback to old endpoint
            data = self._post("DNI", {"nro_documento": dni})

        if data.get("success") != 1:
            return {"found": False, "error": data.get("message", "Not found")}

        ap_paterno = data.get("ap_paterno", "")
        ap_materno = data.get("ap_materno", "")
        nombre = data.get("nom_razon", "")
        full_name = f"{ap_paterno} {ap_materno} {nombre}".strip()

        return {
            "found": bool(full_name),
            "ap_paterno": ap_paterno,
            "ap_materno": ap_materno,
            "nombre": nombre,
            "full_name": full_name,
            "telefono": data.get("telefono", ""),
            "direccion": data.get("direccion", ""),
            "nacionalidad": data.get("nacionalidad", "PERÚ"),
            "ambito": data.get("ambito", 0),
            "ubigeo": data.get("ubigeo", 0),
            "paradero": data.get("paradero", ""),
        }

    def lookup_placa(self, placa: str) -> dict:
        """Lookup vehicle by license plate."""
        try:
            data = self._post("Test_Placa_User", {"placa": placa.upper()})
        except Exception:
            data = self._post("PLACA", {"placa": placa.upper()})

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

    def sell_cat(
        self,
        # Customer
        ap_paterno: str,
        ap_materno: str,
        nom_razon: str,
        nro_documento: str,
        t_docu: str = "1",  # 1=DNI
        nacionalidad: str = "PERÚ",
        telefono: str = "",
        direccion: str = "",
        paradero: str = "",
        ambito: int = 200101,
        n_ambito: str = "PIURA",
        ubigeo: int = 0,
        n_ubigeo: str = "",
        # Vehicle
        placa: str = "",
        marca: str = "",
        modelo: str = "",
        año: int = 0,
        asientos: int = 0,
        serie_vehiculo: str = "",
        color_veh: str = "",
        idn_tecnica: int = 0,
        # Pricing
        precio: float = 0,
        ap_extra: float = 0,
        medio_pago: str = "Efectivo",
        monto_efectivo: float = 0,
        monto_digital: float = 0,
    ) -> dict:
        """
        Sell a CAT certificate via AFOCAT API.

        Returns dict with success, certificate number, PDF paths.
        """
        total = precio + ap_extra

        form_data = {
            "idn_tecnica": str(idn_tecnica),
            "nacionalidad": nacionalidad,
            "nom_razon": nom_razon,
            "ap_materno": ap_materno,
            "ap_paterno": ap_paterno,
            "paradero": paradero,
            "t_docu": t_docu,
            "t_doc_name": "DNI" if t_docu == "1" else "RUC",
            "nro_documento": nro_documento,
            "telefono": telefono,
            "direccion": direccion,
            "n_ambito": n_ambito,
            "ambito": str(ambito),
            "n_ubigeo": n_ubigeo,
            "ubigeo": str(ubigeo),
            "color_veh": color_veh,
            "placa": placa.upper(),
            "marca": marca,
            "modelo": modelo,
            "año": str(año),
            "asientos": str(asientos),
            "serie": serie_vehiculo,
            "id_motivo": "",
            "motivo_texto": "",
            "ap_extra": str(ap_extra),
            "cat_precio": str(precio),
            "Cat_Saldo": str(monto_efectivo),
            "Cat_Medio_Digital": medio_pago if medio_pago != "Efectivo" else "",
            "Cat_Monto_Digital": str(monto_digital),
            "cat_idcertificado_": "0",
            "cat_anio": "2026",
            "cat_serie_": "FL",
            "estado_m": "4",
            "duplicado": "false",
            "cat_duplicado": "",
            "tipo_cpe": "",
            "jsonResponse__ruta_up": "",
        }

        self._ensure_login()
        resp = self._client.post("/api/Test_Cat_vender", data=form_data)

        if resp.status_code != 200:
            return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}

        try:
            result = resp.json()
        except Exception:
            return {"success": False, "error": f"Invalid response: {resp.text[:200]}"}

        if result.get("success") != 1:
            return {
                "success": False,
                "error": result.get("message", "Unknown error"),
                "raw": result,
            }

        cert_num = result.get("pdf_cat", "")  # e.g. "FL-003105-2026"
        return {
            "success": True,
            "message": result.get("message", ""),
            "certificate_number": cert_num,
            "pdf_cat": result.get("pdf_cat"),
            "pdf_cpe": result.get("pdf_cpe"),
            "pdf_cat_url": f"{AFOCAT_BASE}/mPDF/REPORTES/CAT/{result.get('pdf_cat', '')}.pdf" if result.get("pdf_cat") else None,
            "pdf_cpe_url": f"{AFOCAT_BASE}/mPDF/REPORTES/BOLETAS/{result.get('pdf_cpe', '')}.pdf" if result.get("pdf_cpe") else None,
        }

    def close(self):
        self._client.close()


# Singleton instance
_client: AfocatClient | None = None


def get_afocat_client() -> AfocatClient:
    global _client
    if _client is None:
        _client = AfocatClient()
    return _client
