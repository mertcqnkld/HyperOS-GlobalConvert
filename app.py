#!/usr/bin/env python3
"""
HyperOS-GlobalConvert - Web Server Entry Point
Runs the zero-dependency embedded web interface on http://localhost:8080
"""

import sys
from web.app import start_server

if __name__ == "__main__":
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    start_server(port)
