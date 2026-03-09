"""
phase1/scraper.py
-----------------
Fetches Play Store reviews for a given app within a rolling date window.
Uses google-play-scraper with pagination via continuation_token.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from google_play_scraper import Sort, reviews

logger = logging.getLogger(__name__)


def fetch_reviews(
    app_id: str,
    window_weeks: int = 12,
    lang: str = "en",
    country: str = "in",
    batch_size: int = 200,
) -> list[dict]:
    """
    Download reviews from the Play Store for *app_id* posted within the
    last *window_weeks* weeks.

    Returns a list of raw review dicts from google-play-scraper.
    Fields available: reviewId, userName, content, score, thumbsUpCount,
                      reviewCreatedVersion, at, replyContent, repliedAt.
    """
    cutoff: datetime = datetime.now(tz=timezone.utc) - timedelta(weeks=window_weeks)
    logger.info(
        "Fetching reviews for %s since %s (window=%d weeks)",
        app_id,
        cutoff.date(),
        window_weeks,
    )

    all_reviews: list[dict] = []
    token = None
    page = 0

    while True:
        page += 1
        result, token = reviews(
            app_id,
            lang=lang,
            country=country,
            sort=Sort.NEWEST,
            count=batch_size,
            continuation_token=token,
        )

        if not result:
            logger.info("No more results after page %d.", page)
            break

        # Filter to window; reviews are NEWEST first so once we pass the
        # cutoff every following review will also be too old.
        within_window = []
        exhausted = False
        for r in result:
            review_date: datetime = r["at"]
            # google-play-scraper returns naive datetimes in UTC
            if review_date.tzinfo is None:
                review_date = review_date.replace(tzinfo=timezone.utc)
            if review_date >= cutoff:
                within_window.append(r)
            else:
                exhausted = True
                break

        all_reviews.extend(within_window)
        logger.info(
            "Page %d: %d reviews fetched, %d within window (total so far: %d).",
            page,
            len(result),
            len(within_window),
            len(all_reviews),
        )

        if exhausted or token is None:
            break

    logger.info("Total raw reviews fetched: %d", len(all_reviews))
    return all_reviews
