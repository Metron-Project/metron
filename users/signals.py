import logging

logger = logging.getLogger(__name__)


def log_user_login(sender, request, user, **kwargs):
    logger.info("%s logged in to Metron", user)
