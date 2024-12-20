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

import argparse
import copy
import json
import os
import uuid
from inspect import signature, Signature
from typing import Callable, Optional, Dict, List

import uvicorn
from fastapi import FastAPI, APIRouter, Depends, Request

import vana
from vana.utils.fast_api_threaded_server import FastAPIThreadedServer
from vana.utils.networking import get_external_ip


class NodeServer:
    """
     The ``NodeServer`` class serves as the server-side interface for a node within the network.

     Relies on a FastAPI router to create endpoints for different message types.

     Example Usage::
        # Define your custom message class
        class MyMessage( Message ):
            input: int = 1
            output: int = None

        # Define a custom request forwarding function using your message class
        def forward( message: MyMessage ) -> MyMessage:
            message.output = 2
            return message

        # Initialize NodeServer object with a custom configuration
        node_server = NodeServer(
            config=my_config,
            wallet=my_wallet,
            port=9090,
            ip="192.0.2.0",
            external_ip="203.0.113.0",
            external_port=7070
        )

        # Attach the endpoint with the specified verification and forward functions.
        node_server.attach(
            forward_fn = forward_my_message
        )

        # Serve and start your NodeServer.
        node_server.serve().start()
    """

    def __init__(self,
                 wallet: Optional["vana.Wallet"] = None,
                 config: Optional["vana.Config"] = None,
                 port: Optional[int] = None,
                 ip: Optional[str] = None,
                 external_ip: Optional[str] = None,
                 external_port: Optional[int] = None,
                 max_workers: Optional[int] = None):
        if config is None:
            config = self.config()
        config = copy.deepcopy(config)
        config.node_server.ip = ip or config.node_server.get("ip", "0.0.0.0")
        config.node_server.port = port or config.node_server.get("port", 4000)
        config.node_server.external_ip = external_ip or config.node_server.get("external_ip", get_external_ip())
        config.node_server.external_port = external_port or config.node_server.get("external_port", 4000)
        config.node_server.max_workers = max_workers or config.node_server.get("max_workers", 5)
        self.check_config(config)
        self.config = config
        self.wallet = wallet

        # Build NodeServer objects.
        self.uuid = str(uuid.uuid1())
        self.ip = self.config.node_server.ip
        self.port = self.config.node_server.port
        self.external_ip = (
            self.config.node_server.external_ip
            if self.config.node_server.external_ip is not None
            else get_external_ip()
        )
        self.external_port = (
            self.config.node_server.external_port
            if self.config.node_server.external_port is not None
            else self.config.node_server.port
        )
        self.full_address = str(self.ip) + ":" + str(self.port)
        self.full_external_address = str(self.external_ip) + ":" + str(self.external_port)
        self.started = False

        # Request default functions.
        self.forward_class_types: Dict[str, List[Signature]] = {}

        # Instantiate FastAPI
        self.app = FastAPI()
        log_level = "info"
        self.fast_config = uvicorn.Config(
            self.app, host="0.0.0.0", port=self.config.node_server.port, log_level=log_level, loop='asyncio',
            workers=config.node_server.max_workers
        )
        self.fast_server = FastAPIThreadedServer(config=self.fast_config)  # uvicorn.Server(self.fast_config)
        self.router = APIRouter()
        self.app.include_router(self.router)

        # Attach default forward.
        def ping(r: vana.Message) -> vana.Message:
            return r

        self.attach(
            forward_fn=ping
        )

        self.attach_cli_input()

    def info(self) -> "vana.NodeServerInfo":
        """Returns the NodeServerInfo object associated with this NodeServer."""
        return vana.NodeServerInfo(
            version=vana.__version_as_int__,
            ip=self.external_ip,
            ip_type=4,
            port=self.external_port,
            hotkey=self.wallet.hotkey.address,
            coldkey=self.wallet.coldkeypub_str,
        )

    def attach(self, forward_fn: Callable) -> "NodeServer":
        """
        Attaches custom functions to the NodeServer for handling incoming requests.
        Registers an API endpoint to the FastAPI application router.
        """
        # Assert 'forward_fn' has exactly one argument
        forward_sig = signature(forward_fn)
        assert (
                len(list(forward_sig.parameters)) == 1
        ), "The passed function must have exactly one argument"

        # Obtain the class of the first argument of 'forward_fn'
        request_class = forward_sig.parameters[
            list(forward_sig.parameters)[0]
        ].annotation

        # Assert that the first argument of 'forward_fn' is a subclass of 'Message'
        assert issubclass(
            request_class, vana.Message
        ), "The argument of forward_fn must inherit from Message"

        # Obtain the class name of the first argument of 'forward_fn'
        request_name = forward_sig.parameters[
            list(forward_sig.parameters)[0]
        ].annotation.__name__

        # Add the endpoint to the router, making it available on both GET and POST methods
        dependencies = [Depends(self.verify_body_integrity)] if self.config.node_server.verify_body_integrity else []
        self.router.add_api_route(
            f"/{request_name}",
            forward_fn,
            methods=["GET", "POST"],
            dependencies=dependencies,
        )
        self.app.include_router(self.router)

        self.forward_class_types[request_name] = forward_sig.parameters[
            list(forward_sig.parameters)[0]
        ].annotation

        return self

    def attach_cli_input(self):
        """
        Temporary route to send commands to the NodeServer via API.
        Creates a file which the validator will pick up, process, and delete.
        """

        def handle_cli_input(r: Request):
            cli_input = r.query_params.get('input')
            if cli_input is not None:
                try:
                    json.loads(cli_input)
                    with open('cli.json', 'w') as f:
                        f.write(cli_input)
                        return {"status": "success"}
                except json.JSONDecodeError:
                    return {"status": "failed", "message": "invalid json"}
            else:
                return {"status": "failed", "message": "missing input query param"}

        self.router.add_api_route(
            f"/cli",
            handle_cli_input,
            methods=["GET"]
        )
        self.app.include_router(self.router)

    @classmethod
    def config(cls) -> vana.Config:
        """
        Parses the command-line arguments to form a configuration object.
        """
        parser = argparse.ArgumentParser()
        NodeServer.add_args(parser)
        return vana.Config(parser, args=[])

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser, prefix: Optional[str] = None):
        """
        Adds NodeServer-specific command-line arguments to the argument parser.
        """
        prefix_str = "" if prefix is None else prefix + "."
        try:
            # Get default values from environment variables or use default values
            default_node_server_port = os.getenv("NODESERVER_PORT") or 8091
            default_node_server_ip = os.getenv("NODESERVER_IP") or "[::]"
            default_node_server_external_port = os.getenv("NODESERVER_EXTERNAL_PORT") or None
            default_node_server_external_ip = os.getenv("NODESERVER_EXTERNAL_IP") or None
            default_node_server_max_workers = os.getenv("NODESERVER_MAX_WORKERS") or 10

            # Add command-line arguments to the parser
            parser.add_argument(
                "--" + prefix_str + "node_server.port",
                type=int,
                help="The local port this NodeServer endpoint is bound to. i.e. 8091",
                default=default_node_server_port,
            )
            parser.add_argument(
                "--" + prefix_str + "node_server.ip",
                type=str,
                help="""The local ip this NodeServer binds to. ie. [::]""",
                default=default_node_server_ip,
            )
            parser.add_argument(
                "--" + prefix_str + "node_server.external_port",
                type=int,
                required=False,
                help="""The public port this NodeServer broadcasts to the network. i.e. 8091""",
                default=default_node_server_external_port,
            )
            parser.add_argument(
                "--" + prefix_str + "node_server.external_ip",
                type=str,
                required=False,
                help="""The external ip this NodeServer broadcasts to the network to. ie. [::]""",
                default=default_node_server_external_ip,
            )
            parser.add_argument(
                "--" + prefix_str + "node_server.max_workers",
                type=int,
                help="""The maximum number connection handler threads working simultaneously on this endpoint.
                            The grpc server distributes new worker threads to service requests up to this number.""",
                default=default_node_server_max_workers,
            )
            parser.add_argument(
                "--" + prefix_str + "node_server.verify_body_integrity",
                type=bool,
                help="""Whether to verify the integrity of the body of incoming HTTP requests.""",
                default=True,
            )

        except argparse.ArgumentError:
            # Exception handling for re-parsing arguments
            pass

    async def verify_body_integrity(self, request: Request):
        """
        Responsible for ensuring the integrity of the body of incoming HTTP requests.
        """
        # Await and load the request body, so we can inspect it
        body = await request.body()
        request_body = body.decode() if isinstance(body, bytes) else body
        request_name = request.url.path.split("/")[1]

        # Load the body dict and check if all required field hashes match
        body_dict = json.loads(request_body)

        # Reconstruct the message object from the body dict and recompute the hash
        syn = self.forward_class_types[request_name](**body_dict)  # type: ignore
        parsed_body_hash = syn.body_hash  # Rehash the body from request

        body_hash = request.headers.get("computed_body_hash", "")
        if parsed_body_hash != body_hash:
            raise ValueError(
                f"Hash mismatch between header body hash {body_hash} and parsed body hash {parsed_body_hash}"
            )

        # If body is good, return the parsed body so that it can be passed onto the route function
        return body_dict

    @classmethod
    def check_config(cls, config: "vana.config"):
        """
        This method checks the configuration for the NodeServer's port and wallet.
        """
        pass

    def start(self) -> "NodeServer":
        self.fast_server.start()  # If using not FastAPIThreadedServer, use self.fast_server.run()
        self.started = True
        return self

    def stop(self) -> "NodeServer":
        # self.fast_server.should_exit = True  # If using FastAPIThreadedServer, use self.fast_server.stop()
        self.fast_server.stop()
        self.started = False
        return self

    def serve(self, dlp_uid: Optional[int] = None, chain_manager: Optional["vana.ChainManager"] = None) -> "NodeServer":
        """
        Registers the NodeServer with a specific DLP within the Vana network, identified by the ``dlp_uid``.
        """
        if chain_manager is not None and hasattr(chain_manager, "serve_node_server"):
            chain_manager.serve_node_server(dlp_uid=dlp_uid, node_server=self)
        return self

    def unserve(self, dlp_uid: int, chain_manager: Optional["vana.ChainManager"] = None) -> "NodeServer":
        """
        De-registers the NodeServer with a specific DLP within the Vana network, identified by the ``dlp_uid``.
        """
        if chain_manager is not None and hasattr(chain_manager, "remove_node_server"):
            chain_manager.remove_node_server(dlp_uid=dlp_uid, node_server=self)
        return self
