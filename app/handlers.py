import logging
from functools import wraps

from flask import g

from app import settings
from app.alexa import AlexaResponse
from app.roku import RokuError

logger = logging.getLogger(__name__)

# Decorators for handler registration

INTENT_HANDLERS = {}
REQUEST_TYPE_HANDLERS = {}


def intent_handler(name):
    """Register an intent handler for the given intent name."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        INTENT_HANDLERS[name] = func
        return wrapper
    return decorator


def request_handler(name):
    """Register an request-type handler for the given request type."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        REQUEST_TYPE_HANDLERS[name] = func
        return wrapper
    return decorator


# Main controller

def dispatch(alexa_request):
    """
    Dispatch the incoming, valid AlexaRequest to the appropriate request-type
    handler.
    """
    request_type = alexa_request.request_type
    request_type_handler = REQUEST_TYPE_HANDLERS.get(request_type)
    if callable(request_type_handler):
        return request_type_handler(alexa_request)
    else:
        logger.error('Unhandled request type: {0}'.format(request_type))
        return AlexaResponse('Sorry, that feature isn\'t ready yet.')


# Request-type handlers

@request_handler('LaunchRequest')
def welcome(alexa_request):
    return AlexaResponse(
        'Welcome to {0}. Try opening a Roku app by saying '
        '"ask {1} to open Netflix."'
        .format(settings.SKILL_NAME, settings.SKILL_INVOCATION_NAME)
    )


@request_handler('IntentRequest')
def intent_dispatcher(alexa_request, intent_name=None):
    """Dispatch the incoming AlexaRequest to the appropriate intent handler."""
    if intent_name is None:
        intent_name = alexa_request.intent_name
    intent_handler = INTENT_HANDLERS.get(intent_name)
    if callable(intent_handler):
        return intent_handler(alexa_request)
    else:
        logger.error('Unhandled intent: {0}'.format(intent_name))
        return AlexaResponse('Sorry, that feature isn\'t ready yet.')


@request_handler('SessionEndedRequest')
def session_ended(alexa_request):
    # No response is allowed for a SessionEndedRequest, but just in case Amazon
    # changes their mind about that...
    return AlexaResponse('Bye!')


# Intent handlers

@intent_handler('AMAZON.HelpIntent')
def help(alexa_request):
    return AlexaResponse(
        '{0} can open Roku apps, play and pause, and send other button presses '
        'to your Roku.'
        .format(settings.SKILL_NAME)
    )


@intent_handler('LaunchChannelIntent')
def launch_channel(alexa_request):
    channel = alexa_request.slots['Channel'].get('value')
    if g.roku.get_channel(channel) is None:
        response = AlexaResponse(
            'I couldn\'t find a channel named {0}.'.format(channel)
        )
    else:
        g.roku.launch_channel(channel)
        response = AlexaResponse('Opening {0}.'.format(channel))
    return response


@intent_handler('PauseIntent')
@intent_handler('PlayIntent')
def play_or_pause(alexa_request):
    g.roku.play_pause()
    return AlexaResponse('Ok.')


@intent_handler('OkayIntent')
@intent_handler('SelectIntent')
def press_ok(alexa_request):
    g.roku.press_ok()
    return AlexaResponse('Ok.')


@intent_handler('PressButtonIntent')
def press_button(alexa_request):
    button = alexa_request.slots['Button'].get('value')
    try:
        g.roku.press_button(button)
    except RokuError as e:
        logger.exception(e)
        return AlexaResponse('Sorry, something went wrong.')
    else:
        return AlexaResponse('Pressing {0}.'.format(button))