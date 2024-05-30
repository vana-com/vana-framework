import contextlib
import threading
import time

import uvicorn


class FastAPIThreadedServer(uvicorn.Server):
    """
    The ``FastAPIThreadedServer`` class is a specialized server implementation for the NodeServer in the network.

    It extends the functionality of :func:`uvicorn.Server` to run the FastAPI application in a separate thread, allowing the Node Server to handle HTTP requests concurrently and non-blocking.

    This class is designed to facilitate the integration of FastAPI with the Node Server's asynchronous architecture, ensuring efficient and scalable handling of network requests.

    Importance and Functionality
        Threaded Execution
            The class allows the FastAPI application to run in a separate thread, enabling concurrent handling of HTTP requests which is crucial for the performance and scalability of the Node Server.

        Seamless Integration
            By running FastAPI in a threaded manner, this class ensures seamless integration of FastAPI's capabilities with the Node Server's asynchronous and multi-threaded architecture.

        Controlled Server Management
            The methods start and stop provide controlled management of the server's lifecycle, ensuring that the server can be started and stopped as needed, which is vital for maintaining the Node Server's reliability and availability.

        Signal Handling
            Overriding the default signal handlers prevents potential conflicts with the Node Server's main application flow, ensuring stable operation in various network conditions.

    Use Cases
        Starting the Server
            When the Node Server is initialized, it can use this class to start the FastAPI application in a separate thread, enabling it to begin handling HTTP requests immediately.

        Stopping the Server
            During shutdown or maintenance of the Node Server, this class can be used to stop the FastAPI application gracefully, ensuring that all resources are properly released.

    Args:
        should_exit (bool): Flag to indicate whether the server should stop running.
        is_running (bool): Flag to indicate whether the server is currently running.

    The server overrides the default signal handlers to prevent interference with the main application flow and provides methods to start and stop the server in a controlled manner.
    """

    should_exit: bool = False
    is_running: bool = False

    def install_signal_handlers(self):
        """
        Overrides the default signal handlers provided by ``uvicorn.Server``. This method is essential to ensure that the signal handling in the threaded server does not interfere with the main application's flow, especially in a complex asynchronous environment like the Node Server.
        """
        pass

    @contextlib.contextmanager
    def run_in_thread(self):
        """
        Manages the execution of the server in a separate thread, allowing the FastAPI application to run asynchronously without blocking the main thread of the Node Server. This method is a key component in enabling concurrent request handling in the Node Server.

        Yields:
            None: This method yields control back to the caller while the server is running in the background thread.
        """
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        try:
            while not self.started:
                time.sleep(1e-3)
            yield
        finally:
            self.should_exit = True
            thread.join()

    def _wrapper_run(self):
        """
        A wrapper method for the :func:`run_in_thread` context manager. This method is used internally by the ``start`` method to initiate the server's execution in a separate thread.
        """
        with self.run_in_thread():
            while not self.should_exit:
                time.sleep(1e-3)

    def start(self):
        """
        Starts the FastAPI server in a separate thread if it is not already running. This method sets up the server to handle HTTP requests concurrently, enabling the Node Server to efficiently manage
        incoming network requests.

        The method ensures that the server starts running in a non-blocking manner, allowing the Node Server to continue its other operations seamlessly.
        """
        if not self.is_running:
            self.should_exit = False
            thread = threading.Thread(target=self._wrapper_run, daemon=True)
            thread.start()
            self.is_running = True

    def stop(self):
        """
        Signals the FastAPI server to stop running. This method sets the :func:`should_exit` flag to ``True``, indicating that the server should cease its operations and exit the running thread.

        Stopping the server is essential for controlled shutdowns and resource management in the Node Server, especially during maintenance or when redeploying with updated configurations.
        """
        if self.is_running:
            self.should_exit = True
