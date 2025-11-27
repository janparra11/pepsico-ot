# config/middlewares.py

from django.utils.deprecation import MiddlewareMixin


class NoCacheMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # Evitar que el navegador guarde en caché páginas protegidas
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
        return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # Content Security Policy básica
        # Ajusta si usas CDNs externos (Google Fonts, etc.)
        csp = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
        )
        # Solo la seteamos si no existe ya
        response.setdefault("Content-Security-Policy", csp)

        # Referrer-Policy recomendable
        response.setdefault("Referrer-Policy", "same-origin")

        return response
