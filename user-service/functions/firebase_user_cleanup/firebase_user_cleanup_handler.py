"""Delete Firebase Auth users when user deletion events are emitted."""
import json
import logging
import os
from typing import Any, Dict

import boto3
import firebase_admin
from firebase_admin import auth, credentials

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

secrets_client = boto3.client("secretsmanager")
_service_account_secret_name = os.environ["FIREBASE_SERVICE_ACCOUNT_SECRET_NAME"]


def _initialize_firebase() -> None:
    """Initialize Firebase Admin SDK once per execution environment."""
    if firebase_admin._apps:
        return

    secret_response = secrets_client.get_secret_value(SecretId=_service_account_secret_name)
    secret_string = secret_response.get("SecretString")
    if not secret_string:
        raise ValueError("Firebase service account secret has no SecretString payload")

    service_account_info = json.loads(secret_string)
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    request_id = context.aws_request_id if context else "unknown"
    detail = event.get("detail") or {}
    user_id = detail.get("userId")

    if not user_id:
        logger.warning(
            "Skipping event without userId",
            extra={"request_id": request_id, "event": event},
        )
        return {"status": "ignored", "reason": "missing_user_id"}

    try:
        _initialize_firebase()
        auth.delete_user(user_id)
        logger.info(
            "Deleted Firebase Auth user",
            extra={"request_id": request_id, "user_id": user_id},
        )
        return {"status": "deleted", "userId": user_id}
    except auth.UserNotFoundError:
        # Idempotency: deleting an already removed Firebase user should not fail retries.
        logger.info(
            "Firebase Auth user already absent",
            extra={"request_id": request_id, "user_id": user_id},
        )
        return {"status": "already_deleted", "userId": user_id}
    except Exception:
        logger.exception(
            "Failed to delete Firebase Auth user",
            extra={"request_id": request_id, "user_id": user_id},
        )
        raise
