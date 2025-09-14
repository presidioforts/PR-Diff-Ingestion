#!/usr/bin/env python3
"""Startup script for P1 Diff API server."""

import argparse
import sys
from pathlib import Path

# Add src to path so we can import p1diff
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import uvicorn
except ImportError:
    print("Error: uvicorn not installed. Run: pip install -r requirements.txt")
    sys.exit(1)


def main():
    """Main entry point for API server."""
    parser = argparse.ArgumentParser(
        description="Start P1 Diff API server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/start_api.py                    # Development server
  python scripts/start_api.py --host 0.0.0.0    # Listen on all interfaces
  python scripts/start_api.py --workers 4       # Production with 4 workers
  python scripts/start_api.py --reload          # Auto-reload on changes
        """
    )
    
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Log level (default: info)"
    )
    
    args = parser.parse_args()
    
    print(f"🚀 Starting P1 Diff API server...")
    print(f"   Host: {args.host}")
    print(f"   Port: {args.port}")
    print(f"   Workers: {args.workers}")
    print(f"   Reload: {args.reload}")
    print(f"   Log Level: {args.log_level}")
    print(f"   API Docs: http://{args.host}:{args.port}/docs")
    print()
    
    # Configure uvicorn
    config = {
        "app": "p1diff.api.app:app",
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level,
    }
    
    if args.reload:
        config["reload"] = True
        config["reload_dirs"] = ["src"]
    else:
        config["workers"] = args.workers
    
    # Start server
    uvicorn.run(**config)


if __name__ == "__main__":
    main()
