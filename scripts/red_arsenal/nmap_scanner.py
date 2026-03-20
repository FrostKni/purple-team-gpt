#!/usr/bin/env python3
"""
Nmap Scanner Tool for Red Team Operations
Performs network scanning and port discovery using nmap.
"""

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Nmap network scanner for red team operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -t 192.168.1.1
  %(prog)s -t 192.168.1.0/24 -sV -sC
  %(prog)s -t target.example.com -p 22,80,443
        """
    )
    parser.add_argument(
        "-t", "--target",
        required=True,
        help="Target IP, hostname, or network range (e.g., 192.168.1.1 or 192.168.1.0/24)"
    )
    parser.add_argument(
        "-p", "--ports",
        default=None,
        help="Port specification (e.g., 22,80,443 or 1-1000)"
    )
    parser.add_argument(
        "-sS", "--syn-scan",
        action="store_true",
        help="Perform SYN scan (requires root)"
    )
    parser.add_argument(
        "-sT", "--tcp-scan",
        action="store_true",
        default=True,
        help="Perform TCP connect scan (default)"
    )
    parser.add_argument(
        "-sV", "--version-detection",
        action="store_true",
        help="Enable version detection"
    )
    parser.add_argument(
        "-sC", "--script-scan",
        action="store_true",
        help="Enable default script scan"
    )
    parser.add_argument(
        "-O", "--os-detection",
        action="store_true",
        help="Enable OS detection (requires root)"
    )
    parser.add_argument(
        "-A", "--aggressive",
        action="store_true",
        help="Enable aggressive scan (OS detection, version detection, script scan, traceroute)"
    )
    parser.add_argument(
        "-T", "--timing",
        type=int,
        choices=range(0, 6),
        default=3,
        help="Timing template (0=paranoid, 5=insane)"
    )
    parser.add_argument(
        "--top-ports",
        type=int,
        default=None,
        help="Scan top N ports"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file for results (JSON format)"
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Simulate scan (for testing without nmap installed)"
    )
    return parser.parse_args()


def build_nmap_command(args: argparse.Namespace) -> list:
    """Build the nmap command based on arguments."""
    cmd = ["nmap"]
    
    # Scan types
    if args.syn_scan:
        cmd.append("-sS")
    elif args.tcp_scan:
        cmd.append("-sT")
    
    if args.version_detection:
        cmd.append("-sV")
    
    if args.script_scan:
        cmd.append("-sC")
    
    if args.os_detection:
        cmd.append("-O")
    
    if args.aggressive:
        cmd.append("-A")
    
    # Timing
    cmd.append(f"-T{args.timing}")
    
    # Ports
    if args.ports:
        cmd.extend(["-p", args.ports])
    elif args.top_ports:
        cmd.extend(["--top-ports", str(args.top_ports)])
    
    # Output format
    cmd.extend(["-oX", "-"])  # XML output to stdout
    
    # Target
    cmd.append(args.target)
    
    return cmd


def parse_nmap_xml(xml_output: str) -> dict:
    """Parse nmap XML output into structured data."""
    result = {
        "hosts": [],
        "scan_info": {}
    }
    
    try:
        root = ET.fromstring(xml_output)
        
        # Parse scan info
        for scaninfo in root.findall(".//scaninfo"):
            result["scan_info"] = {
                "type": scaninfo.get("type", ""),
                "protocol": scaninfo.get("protocol", ""),
                "numservices": scaninfo.get("numservices", "")
            }
        
        # Parse hosts
        for host in root.findall(".//host"):
            host_data = {
                "address": "",
                "hostnames": [],
                "ports": [],
                "os": None,
                "status": ""
            }
            
            # Status
            status = host.find("status")
            if status is not None:
                host_data["status"] = status.get("state", "unknown")
            
            # Addresses
            for addr in host.findall("address"):
                if addr.get("addrtype") == "ipv4":
                    host_data["address"] = addr.get("addraddr", "")
                elif addr.get("addrtype") == "ipv6":
                    host_data["address"] = addr.get("addraddr", "")
            
            # Hostnames
            hostnames = host.find("hostnames")
            if hostnames is not None:
                for hostname in hostnames.findall("hostname"):
                    host_data["hostnames"].append({
                        "name": hostname.get("name", ""),
                        "type": hostname.get("type", "")
                    })
            
            # Ports
            ports = host.find("ports")
            if ports is not None:
                for port in ports.findall("port"):
                    port_data = {
                        "port": int(port.get("portid", 0)),
                        "protocol": port.get("protocol", ""),
                        "state": "",
                        "service": "",
                        "version": "",
                        "scripts": []
                    }
                    
                    state = port.find("state")
                    if state is not None:
                        port_data["state"] = state.get("state", "")
                    
                    service = port.find("service")
                    if service is not None:
                        port_data["service"] = service.get("name", "")
                        port_data["version"] = service.get("version", "")
                    
                    # Script results
                    for script in port.findall(".//script"):
                        port_data["scripts"].append({
                            "id": script.get("id", ""),
                            "output": script.get("output", "")
                        })
                    
                    if port_data["state"] == "open":
                        host_data["ports"].append(port_data)
            
            # OS detection
            os_match = host.find("os")
            if os_match is not None:
                osmatch = os_match.find("osmatch")
                if osmatch is not None:
                    host_data["os"] = {
                        "name": osmatch.get("name", ""),
                        "accuracy": osmatch.get("accuracy", "")
                    }
            
            result["hosts"].append(host_data)
    
    except ET.ParseError as e:
        result["error"] = f"Failed to parse XML: {str(e)}"
    
    return result


def simulate_scan(args: argparse.Namespace) -> dict:
    """Simulate a scan for testing purposes."""
    return {
        "success": True,
        "tool": "nmap_scanner",
        "target": args.target,
        "timestamp": datetime.now().isoformat(),
        "scan_info": {
            "type": "connect",
            "protocol": "tcp",
            "numservices": "1000"
        },
        "hosts": [
            {
                "address": "192.168.1.1",
                "hostnames": [{"name": "target.example.com", "type": "PTR"}],
                "status": "up",
                "ports": [
                    {"port": 22, "protocol": "tcp", "state": "open", "service": "ssh", "version": "OpenSSH 8.9", "scripts": []},
                    {"port": 80, "protocol": "tcp", "state": "open", "service": "http", "version": "nginx 1.18.0", "scripts": []},
                    {"port": 443, "protocol": "tcp", "state": "open", "service": "https", "version": "nginx 1.18.0", "scripts": []}
                ],
                "os": {"name": "Linux 4.15", "accuracy": "95"}
            }
        ],
        "command_used": "nmap -sT -T3 -oX - " + args.target
    }


def run_nmap_scan(args: argparse.Namespace) -> dict:
    """Execute nmap scan and return results."""
    cmd = build_nmap_command(args)
    
    result = {
        "success": False,
        "tool": "nmap_scanner",
        "target": args.target,
        "timestamp": datetime.now().isoformat(),
        "command_used": " ".join(cmd)
    }
    
    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        if process.returncode == 0:
            parsed = parse_nmap_xml(process.stdout)
            result.update(parsed)
            result["success"] = True
        else:
            result["error"] = process.stderr
            result["returncode"] = process.returncode
    
    except subprocess.TimeoutExpired:
        result["error"] = "Scan timed out after 600 seconds"
    except FileNotFoundError:
        result["error"] = "nmap not found. Please install nmap."
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
    
    return result


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    if args.simulate:
        result = simulate_scan(args)
    else:
        result = run_nmap_scan(args)
    
    # Output JSON
    output_json = json.dumps(result, indent=2)
    print(output_json)
    
    # Write to file if specified
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(output_json)
    
    return 0 if result.get("success", False) else 1


if __name__ == "__main__":
    sys.exit(main())