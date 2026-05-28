import logging

from channels import Group
from channels.auth import channel_session_user, channel_session_user_from_http

from django_nyt import models
from django_nyt.conf import app_settings

logger = logging.getLogger(__name__)


def get_subscriptions(message):
    """
    :return: Subscription query for a given message's user
    """
    if message.user.is_authenticated:
        return models.Subscription.objects.filter(settings__user=message.user)
    return models.Subscription.objects.none()


@channel_session_user_from_http
def ws_connect(message):
    """
    Connected to websocket.connect
    """
    logger.debug("Adding new connection for user %s", message.user)
    message.reply_channel.send({"accept": True})

    for subscription in get_subscriptions(message):
        Group(
            app_settings.NOTIFICATION_CHANNEL.format(
                notification_key=subscription.notification_type.key
            )
        ).add(message.reply_channel)


@channel_session_user
def ws_disconnect(message):
    """
    Connected to websocket.disconnect
    """
    logger.debug("Removing connection for user %s (disconnect)", message.user)
    for subscription in get_subscriptions(message):
        Group(
            app_settings.NOTIFICATION_CHANNEL.format(
                notification_key=subscription.notification_type.key
            )
        ).discard(message.reply_channel)


def ws_receive(message):
    """
    Receives messages, this is currently just for debugging purposes as there
    is no communication API for the websockets.
    """
    logger.debug("Received a message, responding with a non-API message")
    message.reply_channel.send({"text": "OK"})
