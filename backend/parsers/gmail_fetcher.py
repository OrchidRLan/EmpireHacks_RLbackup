"""
Gmail Fetcher
=============
Thin wrapper around the Gmail API that fetches StreetEasy alert emails
and hands raw message dicts to StreetEasyEmailParser.

Authentication
--------------
We use OAuth 2.0 with a stored token file (token.json).  On first run,
the user is prompted to authorise the app via a browser.  After that,
the refresh token is stored and reused automatically.

Required pip packages:
    google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

Required files (see README):
    credentials.json   — OAuth client credentials downloaded from Google Cloud Console
    token.json         — auto-created on first run; store securely, do not commit
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# modify scope is required to mark messages as read.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# Query used to find unread StreetEasy alert emails.
STREETEASY_QUERY = "from:noreply@email.streeteasy.com is:unread"


class GmailFetcher:
    """
    Fetches unread StreetEasy alert emails from a Gmail account via the Gmail API,
    and marks each message as read once it has been successfully fetched.

    Parameters
    ----------
    credentials_path:
        Path to the OAuth client credentials JSON file downloaded from
        Google Cloud Console.
    token_path:
        Path where the OAuth token will be persisted between runs.
        Defaults to 'token.json' in the working directory.
    """

    def __init__(
        self,
        credentials_path: str = "credentials.json",
        token_path: str = "token.json",
        query_override: str | None = None,
    ) -> None:
        self._credentials_path = credentials_path
        self._token_path = token_path
        self._query_override = query_override   # replaces STREETEASY_QUERY when set
        self._service = None  # lazy init

    # ---------------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------------

    def fetch_new_messages(
        self,
        max_results: int = 50,
        after_date: Optional[str] = None,
    ) -> list[dict]:
        """
        Return a list of raw Gmail message dicts for unread StreetEasy alert emails.
        Each successfully fetched message is marked as read immediately.

        Each dict contains a 'raw' key with the base64url-encoded RFC 2822
        message body, which can be passed directly to
        StreetEasyEmailParser.parse_gmail_message().

        Parameters
        ----------
        max_results:
            Maximum number of messages to fetch per call.
        after_date:
            Optional RFC 3339 date string (YYYY/MM/DD) to filter messages
            received after this date, e.g. "2026/03/01".
        """
        service = self._get_service()
        query = self._query_override if self._query_override is not None else STREETEASY_QUERY
        if after_date:
            query += f" after:{after_date}"

        logger.info("Querying Gmail with: %s", query)

        # Fetch message IDs.
        response = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
        message_stubs = response.get("messages", [])
        logger.info("Found %d unread StreetEasy emails.", len(message_stubs))

        # Fetch full raw message for each ID, then mark as read.
        raw_messages: list[dict] = []
        for stub in message_stubs:
            msg_id = stub["id"]
            try:
                raw = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg_id, format="raw")
                    .execute()
                )
                raw_messages.append(raw)
                self._mark_as_read(msg_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to fetch message %s: %s", msg_id, exc)

        return raw_messages

    # ---------------------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------------------

    def _mark_as_read(self, msg_id: str) -> None:
        """Remove the UNREAD label from a message, marking it as read."""
        try:
            self._get_service().users().messages().modify(
                userId="me",
                id=msg_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()
            logger.debug("Marked message %s as read.", msg_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to mark message %s as read: %s", msg_id, exc)

    # ---------------------------------------------------------------------------
    # Auth helpers
    # ---------------------------------------------------------------------------

    def _get_service(self):
        if self._service is None:
            creds = self._load_or_refresh_credentials()
            self._service = build("gmail", "v1", credentials=creds)
        return self._service

    def _load_or_refresh_credentials(self) -> Credentials:
        creds: Optional[Credentials] = None

        # Load stored token if it exists.
        if os.path.exists(self._token_path):
            creds = Credentials.from_authorized_user_file(self._token_path, SCOPES)

        # Refresh or run the OAuth flow.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired Gmail OAuth token.")
                creds.refresh(Request())
            else:
                logger.info(
                    "Starting Gmail OAuth flow. "
                    "A browser window will open for authorisation."
                )
                if not os.path.exists(self._credentials_path):
                    raise FileNotFoundError(
                        f"Gmail credentials file not found: {self._credentials_path}\n"
                        "Download it from the Google Cloud Console → APIs & Services → Credentials."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self._credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Persist the token for next run.
            with open(self._token_path, "w") as token_file:
                token_file.write(creds.to_json())
            logger.info("Gmail token saved to %s", self._token_path)

        return creds