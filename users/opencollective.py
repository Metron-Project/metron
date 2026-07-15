import http.client
import json
import logging
from datetime import datetime

from django.conf import settings

LOGGER = logging.getLogger(__name__)

HTTP_OK = 200

# Recurring monthly/yearly donations are a single Order with many Transactions over
# time, so querying "orders" would only ever surface a recurring donor's first
# payment. Querying "transactions" instead surfaces every actual charge.
_CONTRIBUTIONS_QUERY = """
query Contributions($slug: String!, $dateFrom: DateTime, $limit: Int!, $offset: Int!) {
  transactions(
    account: [{ slug: $slug }]
    type: CREDIT
    kind: [CONTRIBUTION]
    isRefund: false
    dateFrom: $dateFrom
    limit: $limit
    offset: $offset
  ) {
    totalCount
    nodes {
      id
      createdAt
      amount {
        valueInCents
      }
      fromAccount {
        ... on Individual {
          email
        }
      }
    }
  }
}
"""

PAGE_SIZE = 1000


def fetch_recent_contributions(since: datetime) -> list[dict]:
    """Fetch CONTRIBUTION credit transactions for the collective since the given datetime."""
    contributions: list[dict] = []
    offset = 0

    while True:
        page = _fetch_contributions_page(since, offset)
        if page is None:
            break

        contributions.extend(page["nodes"])
        offset += len(page["nodes"])
        if len(page["nodes"]) < PAGE_SIZE or offset >= page["totalCount"]:
            break

    return contributions


def _fetch_contributions_page(since: datetime, offset: int) -> dict | None:
    conn = None
    try:
        conn = http.client.HTTPSConnection("api.opencollective.com")

        headers = {
            "Content-Type": "application/json",
            "Personal-Token": settings.OPENCOLLECTIVE_API_KEY,
        }
        payload = {
            "query": _CONTRIBUTIONS_QUERY,
            "variables": {
                "slug": settings.OPENCOLLECTIVE_SLUG,
                "dateFrom": since.isoformat(),
                "limit": PAGE_SIZE,
                "offset": offset,
            },
        }

        conn.request("POST", "/graphql/v2", json.dumps(payload), headers)

        res = conn.getresponse()
        body = res.read().decode("utf-8")
        if res.status != HTTP_OK:
            LOGGER.error(
                "Bad response from OpenCollective: %s %s - %s", res.status, res.reason, body
            )
            return None

        data = json.loads(body)
        if "errors" in data:
            LOGGER.error("OpenCollective API returned errors: %s", data["errors"])
            return None

        return data["data"]["transactions"]
    except http.client.HTTPException as e:
        LOGGER.error("HTTP error fetching OpenCollective contributions: %s", e)
        return None
    except (KeyError, json.JSONDecodeError) as e:
        LOGGER.error("Unexpected OpenCollective API response: %s", e)
        return None
    finally:
        if conn is not None:
            conn.close()
