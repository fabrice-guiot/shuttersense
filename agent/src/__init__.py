"""
ShutterSense Agent - Distributed job execution worker.

This package provides the core agent functionality for executing analysis
jobs on user-owned hardware. The agent polls the ShutterSense server for
available jobs, executes them locally, and reports progress via WebSocket.

Key modules:
- main: Entry point and main polling loop
- config: Agent configuration management
- api_client: HTTP/WebSocket client for server communication
- job_executor: Tool execution wrapper
- progress_reporter: Real-time progress streaming
- credential_store: Local encrypted credential storage
- config_loader: ApiConfigLoader for tool configuration
"""

__version__ = "0.1.0"
