import json
import traceback
import copy
from logging import Handler, CRITICAL, ERROR, WARNING, INFO, FATAL, DEBUG, NOTSET, Formatter

import six
import slacker

ERROR_COLOR = 'danger'
WARNING_COLOR = 'warning'
INFO_COLOR = '#439FE0'

COLORS = {
    CRITICAL: ERROR_COLOR,
    FATAL: ERROR_COLOR,
    ERROR: ERROR_COLOR,
    WARNING: WARNING_COLOR,
    INFO: INFO_COLOR,
    DEBUG: INFO_COLOR,
    NOTSET: INFO_COLOR,
}

DEFAULT_EMOJI = ':heavy_exclamation_mark:'


class NoStacktraceFormatter(Formatter):
    def formatException(self, ei):
        return None


class SlackerLogHandler(Handler):
    def __init__(self, api_key, channel, stack_trace=True, username='Python logger', icon_url=None, icon_emoji=None,
                 fail_silent=False, ping_users=None, ping_level=None):
        Handler.__init__(self)
        self.formatter = NoStacktraceFormatter()
        self.stack_trace = stack_trace
        self.fail_silent = fail_silent
        self.slacker = slacker.Slacker(api_key)
        self.username = username
        self.icon_url = icon_url
        self.icon_emoji = icon_emoji if (icon_emoji or icon_url) else DEFAULT_EMOJI
        self.channel = channel if channel.startswith('#') or channel.startswith('@') else '#' + channel
        self.ping_level = ping_level
        self.ping_users = []

    def build_msg(self, record):
        clean_record = copy.copy(record)
        clean_record.exc_info = None
        clean_record.exc_text = None
        clean_record.stack_info = None
        return six.text_type(self.format(clean_record))

    def build_trace(self, record, fallback):
        trace = {
            'fallback': fallback,
            'color': COLORS.get(record.levelno, INFO_COLOR)
        }

        if record.exc_info:
            trace['text'] = ''.join(traceback.format_exception(*record.exc_info))

        return trace

    def emit(self, record):
        message = self.build_msg(record)

        if self.ping_users and record.levelno >= self.ping_level:
            for user in self.ping_users:
                message = '<@%s> %s' % (user, message)

        # 1) Post the main message
        resp = self.slacker.chat.post_message(
            channel=self.channel,
            text=message,
            username=self.username,
            icon_url=self.icon_url,
            icon_emoji=self.icon_emoji,
        )

        # 2) If there is a traceback, reply in a thread
        if self.stack_trace and record.exc_info:
            trace_text = ''.join(traceback.format_exception(*record.exc_info))

            parent_ts = resp.body['ts']  # Slacker response body contains Slack API ts

            self.slacker.chat.post_message(
                channel=self.channel,
                text="```%s```" % trace_text,
                username=self.username,
                icon_url=self.icon_url,
                icon_emoji=":bug:",
                thread_ts=parent_ts,
            )
