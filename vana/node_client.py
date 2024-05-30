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

import asyncio
import time
import uuid
from typing import Optional, Union, List, AsyncGenerator, Any

import aiohttp
from eth_account.messages import encode_defunct

import vana
from vana.utils.networking import get_external_ip


class NodeClient:
    """
    A client for interacting with a node's server.
    """

    def __init__(
            self, wallet: Optional[vana.Wallet] = None
    ):
        self.uuid = str(uuid.uuid1())
        self.external_ip = get_external_ip()
        self.keypair = (wallet.hotkey if isinstance(wallet, vana.Wallet) else wallet) or vana.Wallet().hotkey
        self.message_history: list = []
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    async def session(self) -> aiohttp.ClientSession:
        """
        An asynchronous property that provides access to the internal `aiohttp <https://github.com/aio-libs/aiohttp>`_ client session.
        Example usage::
            node_client = NodeClient()
            async with (await node_client.session).post( # Use the session to make an HTTP POST request
                url,                                  # URL to send the request to
                headers={...},                        # Headers dict to be sent with the request
                json={...},                           # JSON body data to be sent with the request
                timeout=10,                           # Timeout duration in seconds
            ) as response:
                json_response = await response.json() # Extract the JSON response from the server
        """
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    def close_session(self):
        """
        Closes the internal `aiohttp <https://github.com/aio-libs/aiohttp>`_ client session synchronously.
        """
        if self._session:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self._session.close())
            self._session = None

    async def aclose_session(self):
        """
        Asynchronously closes the internal `aiohttp <https://github.com/aio-libs/aiohttp>`_ client session.
        """
        if self._session:
            await self._session.close()
            self._session = None

    def _get_endpoint_url(self, target_node_server, request_name):
        """
        Constructs the endpoint URL for a network request to a target NodeServer.
        """
        endpoint = (
            f"0.0.0.0:{str(target_node_server.port)}"
            if target_node_server.ip == str(self.external_ip)
            else f"{target_node_server.ip}:{str(target_node_server.port)}"
        )
        return f"http://{endpoint}/{request_name}"

    def _handle_request_errors(self, message, request_name, exception):
        """
        Handles exceptions that occur during network requests, updating the message with appropriate status codes and messages.

        This method interprets different types of exceptions and sets the corresponding status code and
        message in the message object. It covers common network errors such as connection issues and timeouts.

        Args:
            message: The message object associated with the request.
            request_name: The name of the request during which the exception occurred.
            exception: The exception object caught during the request.

        Note:
            This method updates the message object in-place.
        """
        if isinstance(exception, aiohttp.ClientConnectorError):
            message.node_client.status_code = "503"
            message.node_client.status_message = f"Service at {message.node_server.ip}:{str(message.node_server.port)}/{request_name} unavailable."
        elif isinstance(exception, asyncio.TimeoutError):
            message.node_client.status_code = "408"
            message.node_client.status_message = (
                f"Timedout after {message.timeout} seconds."
            )
        else:
            message.node_client.status_code = "422"
            message.node_client.status_message = (
                f"Failed to parse response object with error: {str(exception)}"
            )

    def _log_outgoing_request(self, message):
        """
        Logs information about outgoing requests for debugging purposes.
        """
        vana.logging.trace(
            f"node_client | --> | {message.get_total_size()} B | {message.name} | {message.node_server.hotkey} | {message.node_server.ip}:{str(message.node_server.port)} | 0 | Success"
        )

    def _log_incoming_response(self, message):
        """
        Logs information about incoming responses for debugging and monitoring.
        """
        vana.logging.trace(
            f"node_client | <-- | {message.get_total_size()} B | {message.name} | {message.node_server.hotkey} | {message.node_server.ip}:{str(message.node_server.port)} | {message.node_client.status_code} | {message.node_client.status_message}"
        )

    def query(self, *args, **kwargs) -> List[Union[AsyncGenerator[Any, Any], vana.Message]]:
        """
        Makes a synchronous request to multiple target NodeServers and returns the responses.

        Cleanup is automatically handled and sessions are closed upon completed requests.

        Args:
            node_servers (Union[List[Union['NodeServerInfo', 'NodeServer']], Union['NodeServerInfo', 'NodeServer']]):
                The list of target NodeServer information.
            message (Message, optional): The Message object. Defaults to :func:`Message()`.
            timeout (float, optional): The request timeout duration in seconds.
                Defaults to ``12.0`` seconds.
        Returns:
            Union[Message, List[Message]]: If a single target node_server is provided, returns the response from that node_server. If multiple target node_servers are provided, returns a list of responses from all target node_servers.
        """
        result = None
        try:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self.forward(*args, **kwargs))
        except:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            result = new_loop.run_until_complete(self.forward(*args, **kwargs))
            new_loop.close()
        finally:
            self.close_session()
            return result

    async def forward(
            self,
            node_servers: Union[
                List[Union[vana.NodeServerInfo, vana.NodeServer]],
                Union[vana.NodeServerInfo, vana.NodeServer],
            ],
            message: vana.Message = vana.Message(),
            timeout: float = 60,
            deserialize: bool = True,
            run_async: bool = True,
    ) -> List[
        Union[AsyncGenerator[Any, Any], vana.Message]
    ]:
        """
        Asynchronously sends requests to one or multiple NodeServers and collates their responses.
        """
        is_list = True
        # If a single node_servers is provided, wrap it in a list for uniform processing
        if not isinstance(node_servers, list):
            is_list = False
            node_servers = [node_servers]

        async def query_all_node_servers() -> Union[AsyncGenerator[Any, Any], vana.Message]:
            """
            Handles the processing of requests to all targeted node_servers
            """

            async def single_node_server_response(target_node_server) -> Union[AsyncGenerator[Any, Any], vana.Message]:
                """
                Manages the request and response process for a single node_server
                """
                return await self.call(
                    target_node_server=target_node_server,
                    message=message.copy(),
                    timeout=timeout,
                    deserialize=deserialize,
                )

            # If run_async flag is False, get responses one by one.
            if not run_async:
                return [await single_node_server_response(target_node_server) for target_node_server in node_servers]
            # If run_async flag is True, get responses concurrently using asyncio.gather().
            return await asyncio.gather(
                *(single_node_server_response(target_node_server) for target_node_server in node_servers))

        # Get responses for all node_servers.
        responses = await query_all_node_servers()
        # Return the single response if only one node_server was targeted, else return all responses
        return responses[0] if len(responses) == 1 and not is_list else responses

    async def call(
            self,
            target_node_server: Union[vana.NodeServerInfo, vana.NodeServer],
            message: vana.Message = vana.Message(),
            timeout: float = 12.0,
            deserialize: bool = True,
    ) -> vana.Message:
        """
        Asynchronously sends a request to a specified NodeServer and processes the response.
        """

        # Record start time
        start_time = time.time()
        target_node_server = (
            target_node_server.info()
            if isinstance(target_node_server, vana.NodeServer)
            else target_node_server
        )

        # Build request endpoint from the message class
        request_name = message.__class__.__name__
        url = self._get_endpoint_url(target_node_server, request_name=request_name)

        # Preprocess message for making a request
        message = self.preprocess_message_for_request(target_node_server, message, timeout)

        try:
            # Log outgoing request
            self._log_outgoing_request(message)

            # Make the HTTP POST request
            async with (await self.session).post(
                    url,
                    headers=message.to_headers(),
                    json=message.dict(),
                    timeout=timeout,
            ) as response:
                # Extract the JSON response from the server
                json_response = await response.json()
                # Process the server response and fill message
                self.process_server_response(response, json_response, message)

            # Set process time and log the response
            message.node_client.process_time = str(time.time() - start_time)

        except Exception as e:
            self._handle_request_errors(message, request_name, e)

        finally:
            self._log_incoming_response(message)

            # Log message event history
            self.message_history.append(
                vana.Message.from_headers(message.to_headers())
            )

            # Return the updated message object after deserializing if requested
            if deserialize:
                return message.deserialize()
            else:
                return message

    def preprocess_message_for_request(
            self,
            target_node_server_info: vana.NodeServerInfo,
            message: vana.Message,
            timeout: float = 12.0,
    ) -> vana.Message:
        """
        Preprocesses the message for making a request. This includes building
        headers for NodeClient and NodeServer and signing the request.

        Args:
            target_node_server_info (NodeServerInfo): The target NodeServer information.
            message (Message): The message object to be preprocessed.
            timeout (float, optional): The request timeout duration in seconds.
                Defaults to ``12.0`` seconds.

        Returns:
            Message: The preprocessed message.
        """
        # Set the timeout for the message
        message.timeout = timeout

        # Build the NodeClient headers using the local system's details
        message.node_client = vana.TerminalInfo(
            ip=self.external_ip,
            version=vana.__version_as_int__,
            nonce=time.monotonic_ns(),
            uuid=self.uuid,
            hotkey=self.keypair.address,
        )

        # Build the NodeServer headers using the target NodeServer's details
        message.node_server = vana.TerminalInfo(
            ip=target_node_server_info.ip,
            port=target_node_server_info.port,
            hotkey=target_node_server_info.hotkey,
        )

        # Sign the request using the node_client, NodeServer info, and the message body hash
        message_to_sign = f"{message.node_client.nonce}.{message.node_client.hotkey}.{message.node_server.hotkey}.{message.node_client.uuid}.{message.body_hash}"
        signable_message = encode_defunct(text=message_to_sign)
        message.node_client.signature = f"0x{self.keypair.sign_message(signable_message).signature}"

        return message

    def process_server_response(
            self,
            server_response: aiohttp.ClientResponse,
            json_response: dict,
            local_message: vana.Message,
    ):
        """
        Processes the server response, updates the local message state with the
        server's state and merges headers set by the server.

        Args:
            server_response (object): The `aiohttp <https://github.com/aio-libs/aiohttp>`_ response object from the server.
            json_response (dict): The parsed JSON response from the server.
            local_message (Message): The local message object to be updated.

        Raises:
            None: But errors in attribute setting are silently ignored.
        """
        # Check if the server responded with a successful status code
        if server_response.status == 200:
            # If the response is successful, overwrite local message state with
            # server's state only if the protocol allows mutation. To prevent overwrites,
            # the protocol must set allow_mutation = False
            server_message = local_message.__class__(**json_response)
            for key in local_message.dict().keys():
                try:
                    # Set the attribute in the local message from the corresponding
                    # attribute in the server message
                    setattr(local_message, key, getattr(server_message, key))
                except:
                    # Ignore errors during attribute setting
                    pass

        # Extract server headers and overwrite None values in local message headers
        server_headers = vana.Message.from_headers(server_response.headers)

        # Merge node_client headers
        local_message.node_client.__dict__.update(
            {
                **local_message.node_client.dict(exclude_none=True),
                **server_headers.node_client.dict(exclude_none=True),
            }
        )

        # Merge NodeServer headers
        local_message.node_server.__dict__.update(
            {
                **local_message.node_server.dict(exclude_none=True),
                **server_headers.node_server.dict(exclude_none=True),
            }
        )

        # Update the status code and status message of the node_client to match the NodeServer
        local_message.node_client.status_code = server_response.status
        local_message.node_client.status_message = local_message.node_server.status_message

    def __str__(self) -> str:
        """
        Returns a string representation of the NodeClient object.

        Returns:
            str: The string representation of the NodeClient object in the format :func:`node_client(<user_wallet_address>)`.
        """
        return "node_client({})".format(self.keypair.address)

    def __repr__(self) -> str:
        """
        Returns a string representation of the NodeClient object, acting as a fallback for :func:`__str__()`.

        Returns:
            str: The string representation of the NodeClient object in the format :func:`node_client(<user_wallet_address>)`.
        """
        return self.__str__()

    async def __aenter__(self):
        """
        Asynchronous context manager entry method.

        Enables the use of the ``async with`` statement with the NodeClient instance. When entering the context,
        the current instance of the class is returned, making it accessible within the asynchronous context.

        Returns:
            NodeClient: The current instance of the NodeClient class.

        Usage::

            async with NodeClient() as node_client:
                await node_client.some_async_method()
        """
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """
        Asynchronous context manager exit method.

        Ensures proper cleanup when exiting the ``async with`` context. This method will close the `aiohttp <https://github.com/aio-libs/aiohttp>`_ client session
        asynchronously, releasing any tied resources.

        Args:
            exc_type (Type[BaseException], optional): The type of exception that was raised.
            exc_value (BaseException, optional): The instance of exception that was raised.
            traceback (TracebackType, optional): A traceback object encapsulating the call stack at the point where the exception was raised.

        Usage::

            async with node_client( wallet ) as node_client:
                await node_client.some_async_method()

        Note:
            This automatically closes the session by calling :func:`__aexit__` after the context closes.
        """
        await self.aclose_session()

    def __del__(self):
        """
        NodeClient destructor.

        This method is invoked when the NodeClient instance is about to be destroyed. The destructor ensures that the
        aiohttp client session is closed before the instance is fully destroyed, releasing any remaining resources.

        Note:
            Relying on the destructor for cleanup can be unpredictable. It is recommended to explicitly close sessions using the provided methods or the ``async with`` context manager.

        Usage::

            node_client = NodeClient()
            # ... some operations ...
            del node_client  # This will implicitly invoke the __del__ method and close the session.
        """
        self.close_session()
