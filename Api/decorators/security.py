from functools import wraps
from django.conf import settings
import requests
import logging
import json
from django.http import JsonResponse, HttpResponse
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import re
import logging
import hashlib
import hmac
from utils.sendmessage import *


def verify_webhook_signature(body: bytes, signature: str, app_secret: str) -> bool:
    """
    Validates the request signature from Meta/Facebook using your app secret.
    """
    expected_signature = hmac.new(
        key=app_secret.encode('utf-8'),
        msg=body,  # ✅ Already bytes, no need to encode again
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)


def signature_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        header_signature = request.headers.get("X-Hub-Signature-256", "")
        if not header_signature.startswith("sha256="):
            logging.warning("Missing or invalid signature format.")
            return JsonResponse({"error": "Invalid signature"}, status=403)

        signature = header_signature[7:]  # strip 'sha256='
        body = request.body  # Raw body bytes 

        if not verify_webhook_signature(body, signature, settings.APP_SECRET):
            logging.warning("Signature validation failed.")
            return JsonResponse({"error": "Signature mismatch"}, status=403)

        return view_func(request, *args, **kwargs)

    return _wrapped_view

