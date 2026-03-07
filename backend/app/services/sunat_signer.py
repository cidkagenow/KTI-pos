"""
XML digital signature for SUNAT electronic invoicing.

Signs XML documents using the empresa's .pfx certificate with enveloped signature.
Signature is placed inside ext:ExtensionContent as SUNAT requires.
"""
import logging

from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
from lxml import etree
from signxml import XMLSigner, methods

from app.config import settings

logger = logging.getLogger(__name__)

# Cache loaded certificate
_cached_key = None
_cached_cert = None

NS_EXT = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
NS_DS = "http://www.w3.org/2000/09/xmldsig#"


def load_certificate(pfx_path: str = None, password: str = None):
    """Load private key and certificate from .pfx file."""
    global _cached_key, _cached_cert
    if _cached_key is not None and _cached_cert is not None:
        return _cached_key, _cached_cert

    pfx_path = pfx_path or settings.SUNAT_CERT_PATH
    password = password or settings.SUNAT_CERT_PASSWORD

    if not pfx_path:
        raise ValueError("SUNAT_CERT_PATH no configurado")

    with open(pfx_path, "rb") as f:
        pfx_data = f.read()

    pwd_bytes = password.encode("utf-8") if password else None
    private_key, certificate, chain = pkcs12.load_key_and_certificates(
        pfx_data, pwd_bytes
    )

    if private_key is None or certificate is None:
        raise ValueError("No se pudo extraer la clave privada o certificado del archivo PFX")

    _cached_key = private_key
    _cached_cert = certificate

    logger.info("Certificate loaded: subject=%s", certificate.subject)
    return private_key, certificate


def clear_certificate_cache():
    """Clear cached certificate (useful for testing)."""
    global _cached_key, _cached_cert
    _cached_key = None
    _cached_cert = None


def sign_xml(xml_bytes: bytes) -> bytes:
    """
    Sign XML document and place signature inside ext:ExtensionContent.
    Returns signed XML bytes.
    """
    private_key, certificate = load_certificate()

    # Parse the XML
    root = etree.fromstring(xml_bytes)

    # Get PEM-encoded cert and key for signxml
    cert_pem = certificate.public_bytes(Encoding.PEM)
    key_pem = private_key.private_bytes(
        Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()
    )

    # Sign using enveloped method (SHA-256, accepted by SUNAT)
    signer = XMLSigner(
        method=methods.enveloped,
        signature_algorithm="rsa-sha256",
        digest_algorithm="sha256",
        c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
    )

    signed_root = signer.sign(
        root,
        key=key_pem,
        cert=cert_pem,
    )

    # signxml places Signature as last child of root.
    # SUNAT requires it inside ext:ExtensionContent.
    # Re-find both elements in the NEW signed tree.
    signature_el = signed_root.find(f"{{{NS_DS}}}Signature")
    ext_content = signed_root.find(f".//{{{NS_EXT}}}ExtensionContent")

    if signature_el is not None and ext_content is not None:
        signed_root.remove(signature_el)
        ext_content.append(signature_el)
    elif signature_el is None:
        raise ValueError("signxml did not produce a Signature element")

    signed_bytes = etree.tostring(signed_root, xml_declaration=True, encoding="UTF-8")
    return signed_bytes
