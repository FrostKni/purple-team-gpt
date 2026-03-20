#!/usr/bin/env python3
"""
Nikto Scanner Tool for Red Team Operations
Performs web server vulnerability scanning using nikto.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Nikto web vulnerability scanner for red team operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -h http://target.example.com
  %(prog)s -h https://192.168.1.1 -p 8443
  %(prog)s -h http://target.com --ssl -port 443
        """
    )
    parser.add_argument(
        "--host",
        required=True,
        help="Target host URL or IP (e.g., http://192.168.1.1)"
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=None,
        help="Target port (default: 80 for HTTP, 443 for HTTPS)"
    )
    parser.add_argument(
        "--ssl",
        action="store_true",
        help="Force SSL connection"
    )
    parser.add_argument(
        "-i", "--id",
        type=str,
        default=None,
        help="Authentication credentials (user:pass)"
    )
    parser.add_argument(
        "-T", "--tuning",
        type=str,
        default=None,
        help="Scan tuning options (e.g., 123456 for specific tests)"
    )
    parser.add_argument(
        "-e", "--evasion",
        type=str,
        default=None,
        help="Evasion technique ID (1-8)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )
    parser.add_argument(
        "-U", "--useragent",
        type=str,
        default=None,
        help="Custom User-Agent string"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file for results (JSON format)"
    )
    parser.add_argument(
        "--plugins",
        type=str,
        default=None,
        help="Comma-separated list of plugins to run"
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Simulate scan (for testing without nikto installed)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    return parser.parse_args()


def build_nikto_command(args: argparse.Namespace) -> list:
    """Build the nikto command based on arguments."""
    cmd = ["nikto"]
    
    # Host
    cmd.extend(["-h", args.host])
    
    # Port
    if args.port:
        cmd.extend(["-p", str(args.port)])
    
    # SSL
    if args.ssl:
        cmd.append("-ssl")
    
    # Authentication
    if args.id:
        cmd.extend(["-id", args.id])
    
    # Tuning
    if args.tuning:
        cmd.extend(["-T", args.tuning])
    
    # Evasion
    if args.evasion:
        cmd.extend(["-e", args.evasion])
    
    # Timeout
    cmd.extend(["-Timeout", str(args.timeout)])
    
    # User-Agent
    if args.useragent:
        cmd.extend(["-useragent", args.useragent])
    
    # Plugins
    if args.plugins:
        cmd.extend(["-Plugins", args.plugins])
    
    # Output format
    cmd.extend(["-Format", "json"])
    cmd.extend(["-output", "-"])  # Output to stdout
    
    return cmd


def parse_nikto_json(output: str) -> dict:
    """Parse nikto JSON output into structured data."""
    result = {
        "vulnerabilities": [],
        "server_info": {},
        "scan_details": {}
    }
    
    try:
        data = json.loads(output)
        
        # Nikto JSON output structure
        if isinstance(data, dict):
            # Parse server info
            if "host" in data:
                result["server_info"]["host"] = data["host"]
            if "port" in data:
                result["server_info"]["port"] = data["port"]
            if "ip" in data:
                result["server_info"]["ip"] = data["ip"]
            
            # Parse vulnerabilities/items
            items = data.get("items", data.get("vulnerabilities", []))
            for item in items:
                vuln = {
                    "id": item.get("id", ""),
                    "uri": item.get("uri", ""),
                    "method": item.get("method", "GET"),
                    "description": item.get("description", item.get("msg", "")),
                    "severity": classify_severity(item.get("description", "")),
                    "osvdb": item.get("osvdb", ""),
                    "references": []
                }
                result["vulnerabilities"].append(vuln)
        
        elif isinstance(data, list):
            for item in data:
                vuln = {
                    "id": item.get("id", ""),
                    "uri": item.get("uri", ""),
                    "method": item.get("method", "GET"),
                    "description": item.get("description", item.get("msg", "")),
                    "severity": classify_severity(item.get("description", "")),
                    "osvdb": item.get("osvdb", ""),
                    "references": []
                }
                result["vulnerabilities"].append(vuln)
    
    except json.JSONDecodeError as e:
        result["error"] = f"Failed to parse JSON: {str(e)}"
    
    return result


def parse_nikto_text(output: str) -> dict:
    """Parse nikto text output as fallback."""
    result = {
        "vulnerabilities": [],
        "server_info": {},
        "scan_details": {}
    }
    
    lines = output.split("\n")
    
    for line in lines:
        line = line.strip()
        
        # Server banner
        if "Server:" in line:
            match = re.search(r"Server:\s*(.+)", line)
            if match:
                result["server_info"]["server_banner"] = match.group(1).strip()
        
        # Vulnerability findings (OSVDB entries)
        if "+ " in line and "OSVDB" in line:
            match = re.search(r"\+ (.+?):\s*(.+)", line)
            if match:
                vuln = {
                    "id": match.group(1),
                    "description": match.group(2),
                    "severity": classify_severity(match.group(2)),
                    "uri": "",
                    "method": "GET"
                }
                result["vulnerabilities"].append(vuln)
        
        # Generic findings
        elif line.startswith("+"):
            finding = line[1:].strip()
            if finding and "Target IP" not in finding and "Target Port" not in finding:
                vuln = {
                    "id": "info",
                    "description": finding,
                    "severity": classify_severity(finding),
                    "uri": "",
                    "method": "GET"
                }
                result["vulnerabilities"].append(vuln)
    
    return result


def classify_severity(description: str) -> str:
    """Classify vulnerability severity based on description."""
    description = description.lower()
    
    critical_keywords = ["remote code execution", "rce", "sql injection", "file upload", 
                         "command injection", "critical"]
    high_keywords = ["xss", "cross-site scripting", "directory traversal", "path traversal",
                     "authentication bypass", "privilege escalation", "high"]
    medium_keywords = ["information disclosure", "sensitive", "password", "credential",
                       "configuration", "version", "medium"]
    low_keywords = ["info", "information", "banner", "header", "low"]
    
    for keyword in critical_keywords:
        if keyword in description:
            return "critical"
    
    for keyword in high_keywords:
        if keyword in description:
            return "high"
    
    for keyword in medium_keywords:
        if keyword in description:
            return "medium"
    
    for keyword in low_keywords:
        if keyword in description:
            return "low"
    
    return "info"


def simulate_scan(args: argparse.Namespace) -> dict:
    """Simulate a scan for testing purposes."""
    return {
        "success": True,
        "tool": "nikto_scanner",
        "target": args.host,
        "timestamp": datetime.now().isoformat(),
        "server_info": {
            "host": args.host,
            "ip": "192.168.1.100",
            "port": args.port or 443,
            "server_banner": "Apache/2.4.52 (Ubuntu)"
        },
        "vulnerabilities": [
            {
                "id": "OSVDB-1234",
                "uri": "/admin/",
                "method": "GET",
                "description": "Admin directory may be accessible",
                "severity": "medium",
                "osvdb": "1234",
                "references": []
            },
            {
                "id": "OSVDB-5678",
                "uri": "/backup.sql",
                "method": "GET",
                "description": "Potential database backup file exposed",
                "severity": "high",
                "osvdb": "5678",
                "references": []
            },
            {
                "id": "info",
                "uri": "/",
                "method": "GET",
                "description": "Server version disclosed in header",
                "severity": "low",
                "osvdb": "",
                "references": []
            },
            {
                "id": "OSVDB-9012",
                "uri": "/cgi-bin/test.cgi",
                "method": "GET",
                "description": "Potentially vulnerable CGI script",
                "severity": "medium",
                "osvdb": "9012",
                "references": []
            }
        ],
        "summary": {
            "total_findings": 4,
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 1,
            "info": 0
        },
        "command_used": f"nikto -h {args.host} -Format json"
    }


def run_nikto_scan(args: argparse.Namespace) -> dict:
    """Execute nikto scan and return results."""
    cmd = build_nikto_command(args)
    
    result = {
        "success": False,
        "tool": "nikto_scanner",
        "target": args.host,
        "timestamp": datetime.now().isoformat(),
        "command_used": " ".join(cmd)
    }
    
    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout
        )
        
        if process.returncode in [0, 1]:  # Nikto returns 1 for completed scans with findings
            # Try JSON parsing first
            try:
                parsed = parse_nikto_json(process.stdout)
                result.update(parsed)
                result["success"] = True
            except:
                # Fall back to text parsing
                parsed = parse_nikto_text(process.stdout)
                result.update(parsed)
                result["success"] = True
        else:
            result["error"] = process.stderr or process.stdout
            result["returncode"] = process.returncode
    
    except subprocess.TimeoutExpired:
        result["error"] = "Scan timed out after 1800 seconds"
    except FileNotFoundError:
        result["error"] = "nikto not found. Please install nikto."
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
    
    # Calculate summary
    if result.get("vulnerabilities"):
        summary = {
            "total_findings": len(result["vulnerabilities"]),
            "critical": sum(1 for v in result["vulnerabilities"] if v.get("severity") == "critical"),
            "high": sum(1 for v in result["vulnerabilities"] if v.get("severity") == "high"),
            "medium": sum(1 for v in result["vulnerabilities"] if v.get("severity") == "medium"),
            "low": sum(1 for v in result["vulnerabilities"] if v.get("severity") == "low"),
            "info": sum(1 for v in result["vulnerabilities"] if v.get("severity") == "info")
        }
        result["summary"] = summary
    
    return result


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    if args.simulate:
        result = simulate_scan(args)
    else:
        result = run_nikto_scan(args)
    
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