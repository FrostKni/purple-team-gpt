#!/usr/bin/env python3
"""
Log Monitor Tool for Blue Team Operations
Monitors and analyzes log files for security events and anomalies.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Log monitoring and analysis tool for blue team operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --file /var/log/auth.log --analyze
  %(prog)s --file /var/log/apache2/access.log --pattern "401|403|500"
  %(prog)s --file /var/log/syslog --time-range 24h
  %(prog)s --directory /var/log --search "failed password"
        """
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Log file to analyze"
    )
    parser.add_argument(
        "--directory",
        type=str,
        default=None,
        help="Directory containing log files to analyze"
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Perform comprehensive log analysis"
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default=None,
        help="Regex pattern to search for"
    )
    parser.add_argument(
        "--search",
        type=str,
        default=None,
        help="Simple string to search for"
    )
    parser.add_argument(
        "--time-range",
        type=str,
        default=None,
        help="Time range to analyze (e.g., 1h, 24h, 7d, 30d)"
    )
    parser.add_argument(
        "--severity",
        type=str,
        choices=["all", "critical", "high", "medium", "low", "info"],
        default="all",
        help="Minimum severity level to report"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for results (JSON format)"
    )
    parser.add_argument(
        "--follow",
        action="store_true",
        help="Follow log file (like tail -f)"
    )
    parser.add_argument(
        "--lines",
        type=int,
        default=1000,
        help="Number of lines to analyze (default: 1000)"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of top items to display (default: 10)"
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Simulate analysis with sample data"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    return parser.parse_args()


# Known log patterns and their classifications
LOG_PATTERNS = {
    # Authentication patterns
    "failed_login": {
        "pattern": r"failed password|authentication failure|invalid user|login failed",
        "severity": "medium",
        "category": "authentication",
        "description": "Failed login attempt"
    },
    "successful_login": {
        "pattern": r"accepted password|session opened|login succeeded",
        "severity": "info",
        "category": "authentication",
        "description": "Successful login"
    },
    "brute_force": {
        "pattern": r"connection closed by authenticating user|too many authentication failures",
        "severity": "high",
        "category": "authentication",
        "description": "Potential brute force attack"
    },
    "sudo_usage": {
        "pattern": r"sudo:|sudo\[",
        "severity": "low",
        "category": "privilege",
        "description": "Sudo command execution"
    },
    "root_access": {
        "pattern": r"root.*tty|root.*pts|to root on",
        "severity": "high",
        "category": "privilege",
        "description": "Root access detected"
    },
    
    # Network patterns
    "firewall_block": {
        "pattern": r"blocked|dropped|rejected|denied",
        "severity": "medium",
        "category": "firewall",
        "description": "Firewall blocked connection"
    },
    "port_scan": {
        "pattern": r"scan detected|possible port scan",
        "severity": "high",
        "category": "network",
        "description": "Port scan detected"
    },
    "connection_timeout": {
        "pattern": r"connection timed out|timeout waiting for",
        "severity": "low",
        "category": "network",
        "description": "Connection timeout"
    },
    
    # Web server patterns
    "http_error": {
        "pattern": r"\s[45]\d{2}\s",
        "severity": "medium",
        "category": "web",
        "description": "HTTP error response"
    },
    "web_attack": {
        "pattern": r"(union.*select|script.*alert|\.php\?|\.asp\?|exec\(|eval\(|base64_)",
        "severity": "critical",
        "category": "web",
        "description": "Potential web attack"
    },
    "sql_injection": {
        "pattern": r"(union.*select|or\s+1\s*=\s*1|drop table|insert into|delete from)",
        "severity": "critical",
        "category": "web",
        "description": "Potential SQL injection"
    },
    "xss_attempt": {
        "pattern": r"(script>|javascript:|onerror=|onload=)",
        "severity": "high",
        "category": "web",
        "description": "Potential XSS attempt"
    },
    "path_traversal": {
        "pattern": r"(\.\.\/|\.\.\\|%2e%2e)",
        "severity": "high",
        "category": "web",
        "description": "Potential path traversal"
    },
    
    # System patterns
    "service_restart": {
        "pattern": r"restarted|starting|stopping",
        "severity": "low",
        "category": "system",
        "description": "Service state change"
    },
    "disk_space": {
        "pattern": r"disk.*full|no space left|filesystem.*full",
        "severity": "high",
        "category": "system",
        "description": "Disk space issue"
    },
    "out_of_memory": {
        "pattern": r"out of memory|oom-killer|killed process",
        "severity": "critical",
        "category": "system",
        "description": "Out of memory"
    },
    
    # Malware/Intrusion patterns
    "malware_signature": {
        "pattern": r"(trojan|malware|virus|backdoor|shell|exploit)",
        "severity": "critical",
        "category": "malware",
        "description": "Potential malware detected"
    },
    "suspicious_file": {
        "pattern": r"suspicious file|malicious|infected",
        "severity": "high",
        "category": "malware",
        "description": "Suspicious file activity"
    },
    
    # SSH patterns
    "ssh_breakin": {
        "pattern": r"break in attempt|possible break in",
        "severity": "critical",
        "category": "ssh",
        "description": "SSH break-in attempt"
    },
    "ssh_disconnect": {
        "pattern": r"disconnected|connection closed|disconnected from",
        "severity": "info",
        "category": "ssh",
        "description": "SSH disconnection"
    }
}

# IP extraction pattern
IP_PATTERN = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"

# Timestamp patterns
TIMESTAMP_PATTERNS = [
    r"\b(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})\b",  # ISO format
    r"\b(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\b",      # Syslog format
    r"\b(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})\b",      # Apache format
]


def parse_time_range(time_range: str) -> datetime:
    """Parse time range string to datetime."""
    now = datetime.now()
    
    match = re.match(r"(\d+)([hdwm])", time_range.lower())
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        
        if unit == "h":
            return now - timedelta(hours=value)
        elif unit == "d":
            return now - timedelta(days=value)
        elif unit == "w":
            return now - timedelta(weeks=value)
        elif unit == "m":
            return now - timedelta(days=value * 30)  # Approximate
    
    # Default to 24 hours
    return now - timedelta(hours=24)


def extract_timestamp(line: str) -> datetime:
    """Extract timestamp from log line."""
    for pattern in TIMESTAMP_PATTERNS:
        match = re.search(pattern, line)
        if match:
            try:
                ts_str = match.group(1)
                # Try various formats
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", 
                           "%b %d %H:%M:%S", "%d/%b/%Y:%H:%M:%S"]:
                    try:
                        return datetime.strptime(ts_str, fmt)
                    except ValueError:
                        continue
            except:
                pass
    
    return datetime.min


def extract_ips(line: str) -> list:
    """Extract IP addresses from log line."""
    return re.findall(IP_PATTERN, line)


def classify_event(line: str) -> list:
    """Classify log events based on patterns."""
    events = []
    line_lower = line.lower()
    
    for event_type, event_info in LOG_PATTERNS.items():
        if re.search(event_info["pattern"], line_lower):
            events.append({
                "type": event_type,
                "severity": event_info["severity"],
                "category": event_info["category"],
                "description": event_info["description"]
            })
    
    return events


def analyze_log_file(file_path: str, args: argparse.Namespace) -> dict:
    """Analyze a single log file."""
    result = {
        "success": True,
        "file": file_path,
        "timestamp": datetime.now().isoformat(),
        "total_lines": 0,
        "events": [],
        "statistics": {
            "by_severity": Counter(),
            "by_category": Counter(),
            "top_ips": Counter(),
            "top_events": Counter(),
            "timeline": defaultdict(int)
        }
    }
    
    # Time filter
    time_filter = None
    if args.time_range:
        time_filter = parse_time_range(args.time_range)
    
    try:
        path = Path(file_path)
        if not path.exists():
            result["error"] = f"File not found: {file_path}"
            result["success"] = False
            return result
        
        # Read and analyze lines
        with open(path, "r", errors="ignore") as f:
            lines = f.readlines()[-args.lines:]  # Get last N lines
        
        result["total_lines"] = len(lines)
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            # Time filtering
            if time_filter:
                ts = extract_timestamp(line)
                if ts != datetime.min and ts < time_filter:
                    continue
            
            # Extract IPs
            ips = extract_ips(line)
            for ip in ips:
                result["statistics"]["top_ips"][ip] += 1
            
            # Custom pattern search
            if args.pattern:
                if re.search(args.pattern, line, re.IGNORECASE):
                    result["events"].append({
                        "line_number": line_num,
                        "line": line,
                        "ips": ips,
                        "match": "custom_pattern"
                    })
            elif args.search:
                if args.search.lower() in line.lower():
                    result["events"].append({
                        "line_number": line_num,
                        "line": line,
                        "ips": ips,
                        "match": "search"
                    })
            else:
                # Pattern classification
                events = classify_event(line)
                if events:
                    for event in events:
                        result["statistics"]["by_severity"][event["severity"]] += 1
                        result["statistics"]["by_category"][event["category"]] += 1
                        result["statistics"]["top_events"][event["type"]] += 1
                    
                    result["events"].append({
                        "line_number": line_num,
                        "line": line,
                        "ips": ips,
                        "classifications": events
                    })
        
        # Convert Counter objects to regular dicts for JSON serialization
        result["statistics"]["by_severity"] = dict(result["statistics"]["by_severity"])
        result["statistics"]["by_category"] = dict(result["statistics"]["by_category"])
        result["statistics"]["top_ips"] = dict(result["statistics"]["top_ips"].most_common(args.top))
        result["statistics"]["top_events"] = dict(result["statistics"]["top_events"].most_common(args.top))
    
    except Exception as e:
        result["error"] = str(e)
        result["success"] = False
    
    return result


def analyze_directory(dir_path: str, args: argparse.Namespace) -> dict:
    """Analyze all log files in a directory."""
    result = {
        "success": True,
        "directory": dir_path,
        "timestamp": datetime.now().isoformat(),
        "files_analyzed": 0,
        "files": [],
        "aggregated_stats": {
            "total_events": 0,
            "by_severity": Counter(),
            "by_category": Counter(),
            "top_ips": Counter()
        }
    }
    
    try:
        path = Path(dir_path)
        if not path.exists():
            result["error"] = f"Directory not found: {dir_path}"
            result["success"] = False
            return result
        
        # Find log files
        log_files = list(path.glob("*.log")) + list(path.glob("*.log.*"))
        
        for log_file in log_files:
            file_result = analyze_log_file(str(log_file), args)
            result["files"].append({
                "file": str(log_file),
                "success": file_result["success"],
                "event_count": len(file_result.get("events", [])),
                "error": file_result.get("error")
            })
            result["files_analyzed"] += 1
            
            # Aggregate statistics
            if file_result["success"]:
                stats = file_result.get("statistics", {})
                for sev, count in stats.get("by_severity", {}).items():
                    result["aggregated_stats"]["by_severity"][sev] += count
                for cat, count in stats.get("by_category", {}).items():
                    result["aggregated_stats"]["by_category"][cat] += count
                for ip, count in stats.get("top_ips", {}).items():
                    result["aggregated_stats"]["top_ips"][ip] += count
                result["aggregated_stats"]["total_events"] += len(file_result.get("events", []))
        
        # Convert counters
        result["aggregated_stats"]["by_severity"] = dict(result["aggregated_stats"]["by_severity"])
        result["aggregated_stats"]["by_category"] = dict(result["aggregated_stats"]["by_category"])
        result["aggregated_stats"]["top_ips"] = dict(result["aggregated_stats"]["top_ips"].most_common(args.top))
    
    except Exception as e:
        result["error"] = str(e)
        result["success"] = False
    
    return result


def simulate_analysis(args: argparse.Namespace) -> dict:
    """Simulate log analysis for testing."""
    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "file": "simulated_log",
        "total_lines": 1000,
        "events": [
            {
                "line_number": 45,
                "line": "Mar 19 10:23:45 server sshd[12345]: Failed password for root from 192.168.1.100 port 22",
                "ips": ["192.168.1.100"],
                "classifications": [
                    {"type": "failed_login", "severity": "medium", "category": "authentication", "description": "Failed login attempt"}
                ]
            },
            {
                "line_number": 78,
                "line": "Mar 19 10:24:12 server sshd[12346]: Failed password for root from 192.168.1.100 port 22",
                "ips": ["192.168.1.100"],
                "classifications": [
                    {"type": "failed_login", "severity": "medium", "category": "authentication", "description": "Failed login attempt"}
                ]
            },
            {
                "line_number": 102,
                "line": "Mar 19 10:25:01 server kernel: [UFW BLOCK] IN=eth0 SRC=10.0.0.50 DST=192.168.1.1",
                "ips": ["10.0.0.50", "192.168.1.1"],
                "classifications": [
                    {"type": "firewall_block", "severity": "medium", "category": "firewall", "description": "Firewall blocked connection"}
                ]
            },
            {
                "line_number": 156,
                "line": '10.0.0.200 - - [19/Mar/2026:10:30:00 +0000] "GET /admin?id=1 UNION SELECT * FROM users HTTP/1.1" 200 1234',
                "ips": ["10.0.0.200"],
                "classifications": [
                    {"type": "sql_injection", "severity": "critical", "category": "web", "description": "Potential SQL injection"}
                ]
            },
            {
                "line_number": 200,
                "line": "Mar 19 10:35:22 server sshd[12400]: Accepted password for admin from 192.168.1.50 port 22",
                "ips": ["192.168.1.50"],
                "classifications": [
                    {"type": "successful_login", "severity": "info", "category": "authentication", "description": "Successful login"}
                ]
            }
        ],
        "statistics": {
            "by_severity": {"medium": 3, "critical": 1, "info": 1},
            "by_category": {"authentication": 3, "firewall": 1, "web": 1},
            "top_ips": {"192.168.1.100": 2, "10.0.0.50": 1, "10.0.0.200": 1, "192.168.1.50": 1},
            "top_events": {"failed_login": 2, "firewall_block": 1, "sql_injection": 1, "successful_login": 1}
        },
        "summary": {
            "total_events": 5,
            "critical_count": 1,
            "high_count": 0,
            "medium_count": 3,
            "low_count": 0,
            "info_count": 1,
            "recommendations": [
                "Investigate repeated failed login attempts from 192.168.1.100",
                "Review SQL injection attempt from 10.0.0.200",
                "Consider blocking suspicious IPs with firewall rules"
            ]
        }
    }


def generate_summary(result: dict) -> dict:
    """Generate a summary of findings."""
    summary = {
        "total_events": len(result.get("events", [])),
        "critical_count": 0,
        "high_count": 0,
        "medium_count": 0,
        "low_count": 0,
        "info_count": 0,
        "recommendations": []
    }
    
    stats = result.get("statistics", {})
    summary["critical_count"] = stats.get("by_severity", {}).get("critical", 0)
    summary["high_count"] = stats.get("by_severity", {}).get("high", 0)
    summary["medium_count"] = stats.get("by_severity", {}).get("medium", 0)
    summary["low_count"] = stats.get("by_severity", {}).get("low", 0)
    summary["info_count"] = stats.get("by_severity", {}).get("info", 0)
    
    # Generate recommendations
    if summary["critical_count"] > 0:
        summary["recommendations"].append("Immediate attention required: Critical security events detected")
    
    top_events = stats.get("top_events", {})
    if "failed_login" in top_events and top_events["failed_login"] > 3:
        summary["recommendations"].append("Multiple failed logins detected - consider account lockout policies")
    
    if "sql_injection" in top_events:
        summary["recommendations"].append("SQL injection attempts detected - review application security")
    
    if "brute_force" in top_events:
        summary["recommendations"].append("Brute force attack detected - implement rate limiting")
    
    top_ips = stats.get("top_ips", {})
    suspicious_ips = [ip for ip, count in top_ips.items() if count > 5]
    if suspicious_ips:
        summary["recommendations"].append(f"Consider blocking suspicious IPs: {', '.join(suspicious_ips[:3])}")
    
    return summary


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    # Handle simulation
    if args.simulate:
        result = simulate_analysis(args)
    elif args.file:
        result = analyze_log_file(args.file, args)
    elif args.directory:
        result = analyze_directory(args.directory, args)
    else:
        result = {
            "success": False,
            "error": "Either --file or --directory must be specified"
        }
    
    # Generate summary
    if result.get("success") and "events" in result:
        result["summary"] = generate_summary(result)
    
    # Output JSON
    output_json = json.dumps(result, indent=2, default=str)
    print(output_json)
    
    # Write to file if specified
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(output_json)
    
    return 0 if result.get("success", False) else 1


if __name__ == "__main__":
    sys.exit(main())