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


def validate_signature(payload, signature):
    """
    Validate the incoming payload's signature against our expected signature
    """
    # Use the App Secret to hash the payload
    expected_signature = hmac.new(
        bytes(settings.APP_SECRET, "latin-1"),
        msg=payload.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Check if the signature matches
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

        if not validate_signature(body, signature, settings.WHATSAPP_APP_SECRET):
            logging.warning("Signature validation failed.")
            return JsonResponse({"error": "Signature mismatch"}, status=403)

        return view_func(request, *args, **kwargs)

    return _wrapped_view