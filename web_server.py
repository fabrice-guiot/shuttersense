#!/usr/bin/env python3
"""
CLI tool to start the ShutterSense FastAPI web server.

This script provides a convenient command-line interface to start the
FastAPI backend server using uvicorn. It validates the master encryption
key before starting and provides helpful error messages.

Usage:
    python3 web_server.py                    # Start with defaults
    python3 web_server.py --host 0.0.0.0     # Listen on all interfaces
    python3 web_server.py --port 8080        # Use custom port
    python3 web_server.py --reload           # Enable auto-reload for development

Environment Variables:
    SHUSAI_MASTER_KEY: Master encryption key (required)
    SHUSAI_DB_URL: PostgreSQL database URL
    SHUSAI_ENV: Environment (production/development, default: development)
    SHUSAI_LOG_LEVEL: Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL)

Example:
    # Start development server with auto-reload
    export SHUSAI_MASTER_KEY="your-key-here"
    python3 web_server.py --reload

    # Start production server on custom port
    python3 web_server.py --host 0.0.0.0 --port 8080
"""

import argparse
import os
import sys
from pathlib import Path


def load_env_file() -> None:
    """
    Load environment variables from backend/.env file.

    Reads the .env file and sets environment variables that are not
    already set in the environment. This allows explicit environment
    variables to take precedence over .env values.
    """
    env_path = Path(__file__).parent / "backend" / ".env"
    if not env_path.exists():
        return

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            # Parse KEY=value
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Only set if not already in environment
                if key and key not in os.environ:
                    os.environ[key] = value


def validate_master_key() -> None:
    """
    Validate that SHUSAI_MASTER_KEY environment variable is set.

    Exits with error code 1 if the master key is not set, providing
    clear instructions on how to set it up.

    Raises:
        SystemExit: If master key is not set
    """
    master_key = os.environ.get("SHUSAI_MASTER_KEY")

    if not master_key:
        print(
            "\n" + "=" * 70,
            "\nERROR: SHUSAI_MASTER_KEY environment variable is not set.",
            "\n\nThe master encryption key is required to start the web server.",
            "\nThis key is used to encrypt/decrypt remote storage credentials",
            "\nstored in the database.",
            "\n\nTo set up the master key, run:",
            "\n  python3 setup_master_key.py",
            "\n\nThis will guide you through generating and configuring the key.",
            "\n\nAfter running setup_master_key.py, set the environment variable:",
            "\n  export SHUSAI_MASTER_KEY='your-key-here'",
            "\n\nOr add it to your shell configuration file (~/.bashrc, ~/.zshrc):",
            "\n  echo 'export SHUSAI_MASTER_KEY=\"your-key-here\"' >> ~/.bashrc",
            "\n" + "=" * 70 + "\n",
            file=sys.stderr
        )
        sys.exit(1)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments namespace with host, port, and reload flags

    Arguments:
        --host: Host to bind (default: 127.0.0.1)
        --port: Port to bind (default: 8000)
        --reload: Enable auto-reload for development (default: False)
    """
    parser = argparse.ArgumentParser(
        description="Start the ShutterSense FastAPI web server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start development server with auto-reload
  python3 web_server.py --reload

  # Start server on all interfaces (accessible from network)
  python3 web_server.py --host 0.0.0.0

  # Start server on custom port
  python3 web_server.py --port 8080

  # Production configuration
  python3 web_server.py --host 0.0.0.0 --port 8000

Environment Variables:
  SHUSAI_MASTER_KEY      Master encryption key (required)
  SHUSAI_DB_URL          PostgreSQL database URL
  SHUSAI_ENV             Environment (production/development)
  SHUSAI_LOG_LEVEL       Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL)

For more information, see docs/quickstart.md
        """
    )

    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind the server to (default: 127.0.0.1). "
             "Use 0.0.0.0 to listen on all interfaces."
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)"
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development. The server will automatically "
             "restart when code changes are detected. Not recommended for production."
    )

    return parser.parse_args()


def main() -> None:
    """
    Main entry point for the web server CLI tool.

    Validates the master key, parses command-line arguments, and starts
    the FastAPI server using uvicorn.

    Exit Codes:
        0: Server stopped normally
        1: Master key validation failed
        2: Uvicorn import error (dependency not installed)
    """
    # Parse command-line arguments first (allows --help without master key)
    args = parse_arguments()

    # Ensure the repo root is on sys.path so "backend.src.main" is importable
    repo_root = str(Path(__file__).parent)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    # Load environment variables from backend/.env
    load_env_file()

    # Validate master key before starting server
    validate_master_key()

    # Import uvicorn (delayed to allow --help without installing dependencies)
    try:
        import uvicorn
    except ImportError:
        print(
            "\n" + "=" * 70,
            "\nERROR: Cannot import uvicorn.",
            f"\n\nCurrent Python interpreter: {sys.executable} (Python {sys.version.split()[0]})",
            "\n\nThis usually means the script is running under a Python interpreter",
            "\nthat does not have the project dependencies installed.",
            "\n\nTo fix this, either:",
            "\n  1. Activate your virtual environment first:",
            "\n       source venv/bin/activate",
            "\n       python3 web_server.py --reload",
            "\n  2. Or run the script with the correct interpreter directly:",
            "\n       /path/to/your/python web_server.py --reload",
            "\n" + "=" * 70 + "\n",
            file=sys.stderr
        )
        sys.exit(2)

    # Print startup information
    print(f"\nStarting ShutterSense web server...")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Auto-reload: {'enabled' if args.reload else 'disabled'}")
    print(f"\nAPI documentation: http://{args.host}:{args.port}/api-docs")
    print(f"Health check: http://{args.host}:{args.port}/health")
    print("\nPress CTRL+C to stop the server\n")

    # Start uvicorn server
    try:
        uvicorn.run(
            "backend.src.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped by user (CTRL+C)")
        sys.exit(0)


if __name__ == "__main__":
    main()
