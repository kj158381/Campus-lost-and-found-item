"""QR code generation for claim hand-over verification."""
import io
import qrcode
from config import Config


def verify_url(token: str) -> str:
    return f"{Config.APP_BASE_URL}/verify/{token}"


def qr_png_bytes(token: str) -> bytes:
    qr = qrcode.QRCode(box_size=9, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(verify_url(token))
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0D1117", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
