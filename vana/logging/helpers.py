# The MIT License (MIT)
# Copyright © 2024 Corsali, Inc. dba Vana

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import logging


def all_loggers():
    """
    Generator that yields all logger instances in the application.
    """
    for logger in logging.root.manager.loggerDict.values():
        if isinstance(logger, logging.PlaceHolder):
            continue
        # In some versions of Python, the values in loggerDict might be
        # LoggerAdapter instances instead of Logger instances.
        # We check for Logger instances specifically.
        if isinstance(logger, logging.Logger):
            yield logger
        else:
            # If it's not a Logger instance, it could be a LoggerAdapter or
            # another form that doesn't directly offer logging methods.
            # This branch can be extended to handle such cases as needed.
            pass


def all_logger_names():
    for name, logger in logging.root.manager.loggerDict.items():
        if isinstance(logger, logging.PlaceHolder):
            continue
        # In some versions of Python, the values in loggerDict might be
        # LoggerAdapter instances instead of Logger instances.
        # We check for Logger instances specifically.
        if isinstance(logger, logging.Logger):
            yield name
        else:
            # If it's not a Logger instance, it could be a LoggerAdapter or
            # another form that doesn't directly offer logging methods.
            # This branch can be extended to handle such cases as needed.
            pass


def get_max_logger_name_length():
    max_length = 0
    for name in all_logger_names():
        if len(name) > max_length:
            max_length = len(name)
    return max_length
