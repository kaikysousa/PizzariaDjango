import secrets

from django.conf import settings


class ContentSecurityPolicyMiddleware:
    """Adiciona CSP com nonce por requisição.

    O admin fica fora da política estrita porque o Django injeta scripts
    inline próprios. A rota é protegida por allowlist no Nginx.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        nonce = secrets.token_urlsafe(16)
        request.csp_nonce = nonce
        response = self.get_response(request)

        if request.path.startswith("/admin/"):
            return response

        if getattr(settings, "CSP_ENABLED", True):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                f"script-src 'self' 'nonce-{nonce}'; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src https://fonts.gstatic.com; "
                "img-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        return response
