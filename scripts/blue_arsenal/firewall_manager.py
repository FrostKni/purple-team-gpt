#!/usr/bin/env python3
"""
Firewall Manager Tool for Blue Team Operations
Manages firewall rules and configurations for network defense.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Firewall management tool for blue team operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --action list
  %(prog)s --action add --rule "block tcp from 192.168.1.100 to any port 22"
  %(prog)s --action remove --rule-id 5
  %(prog)s --action block --ip 10.0.0.50
  %(prog)s --action allow --port 8080 --protocol tcp
        """
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=["list", "add", "remove", "block", "allow", "status", "export", "import"],
        help="Action to perform on firewall"
    )
    parser.add_argument(
        "--rule",
        type=str,
        default=None,
        help="Firewall rule to add (iptables/ufw syntax)"
    )
    parser.add_argument(
        "--rule-id",
        type=int,
        default=None,
        help="Rule ID to remove"
    )
    parser.add_argument(
        "--ip",
        type=str,
        default=None,
        help="IP address for block/allow actions"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port number for allow/block actions"
    )
    parser.add_argument(
        "--protocol",
        type=str,
        choices=["tcp", "udp", "icmp", "all"],
        default="tcp",
        help="Protocol for the rule"
    )
    parser.add_argument(
        "--direction",
        type=str,
        choices=["in", "out", "both"],
        default="in",
        help="Direction of traffic"
    )
    parser.add_argument(
        "--interface",
        type=str,
        default=None,
        help="Network interface (e.g., eth0, wlan0)"
    )
    parser.add_argument(
        "--comment",
        type=str,
        default="",
        help="Comment for the firewall rule"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for results (JSON format)"
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Input file for import action"
    )
    parser.add_argument(
        "--firewall",
        type=str,
        choices=["iptables", "ufw", "firewalld", "auto"],
        default="auto",
        help="Firewall backend to use"
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Simulate operations (for testing)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    return parser.parse_args()


def detect_firewall() -> str:
    """Detect the available firewall backend."""
    # Check for ufw
    try:
        subprocess.run(["ufw", "status"], capture_output=True, check=True)
        return "ufw"
    except:
        pass
    
    # Check for firewalld
    try:
        subprocess.run(["firewall-cmd", "--state"], capture_output=True, check=True)
        return "firewalld"
    except:
        pass
    
    # Check for iptables (always available on Linux)
    try:
        subprocess.run(["iptables", "-L"], capture_output=True, check=True)
        return "iptables"
    except:
        pass
    
    return "iptables"  # Default fallback


def get_iptables_rules() -> list:
    """Get current iptables rules."""
    rules = []
    try:
        result = subprocess.run(
            ["iptables", "-L", "-n", "-v", "--line-numbers"],
            capture_output=True,
            text=True
        )
        
        lines = result.stdout.split("\n")
        current_chain = ""
        
        for line in lines:
            line = line.strip()
            if line.startswith("Chain"):
                current_chain = line.split()[1]
            elif line and line[0].isdigit():
                parts = line.split()
                if len(parts) >= 8:
                    rule = {
                        "id": int(parts[0]),
                        "chain": current_chain,
                        "pkts": parts[1],
                        "bytes": parts[2],
                        "target": parts[3],
                        "protocol": parts[4],
                        "source": parts[5],
                        "destination": parts[6],
                        "options": " ".join(parts[7:]) if len(parts) > 7 else ""
                    }
                    rules.append(rule)
    except Exception as e:
        pass
    
    return rules


def get_ufw_rules() -> list:
    """Get current ufw rules."""
    rules = []
    try:
        result = subprocess.run(
            ["ufw", "status", "numbered"],
            capture_output=True,
            text=True
        )
        
        lines = result.stdout.split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith("["):
                # Parse numbered rule
                parts = line.strip().split("]")
                if len(parts) >= 2:
                    rule_id = parts[0].replace("[", "").strip()
                    rule_text = parts[1].strip()
                    
                    rule = {
                        "id": int(rule_id),
                        "rule": rule_text,
                        "raw": line.strip()
                    }
                    
                    # Parse rule details
                    if "ALLOW" in rule_text:
                        rule["action"] = "allow"
                    elif "DENY" in rule_text or "BLOCK" in rule_text:
                        rule["action"] = "deny"
                    
                    rules.append(rule)
    except Exception as e:
        pass
    
    return rules


def get_firewalld_rules() -> list:
    """Get current firewalld rules."""
    rules = []
    try:
        # Get zones
        zones_result = subprocess.run(
            ["firewall-cmd", "--get-active-zones"],
            capture_output=True,
            text=True
        )
        
        zones = []
        for line in zones_result.stdout.split("\n"):
            if line.strip():
                zones.append(line.split()[0])
        
        # Get rules for each zone
        for zone in zones:
            # Get services
            services = subprocess.run(
                ["firewall-cmd", f"--zone={zone}", "--list-services"],
                capture_output=True,
                text=True
            )
            
            for service in services.stdout.strip().split():
                rules.append({
                    "zone": zone,
                    "type": "service",
                    "value": service,
                    "action": "allow"
                })
            
            # Get ports
            ports = subprocess.run(
                ["firewall-cmd", f"--zone={zone}", "--list-ports"],
                capture_output=True,
                text=True
            )
            
            for port in ports.stdout.strip().split():
                parts = port.split("/")
                rules.append({
                    "zone": zone,
                    "type": "port",
                    "port": parts[0] if parts else port,
                    "protocol": parts[1] if len(parts) > 1 else "tcp",
                    "action": "allow"
                })
            
            # Get rich rules
            rich_rules = subprocess.run(
                ["firewall-cmd", f"--zone={zone}", "--list-rich-rules"],
                capture_output=True,
                text=True
            )
            
            for i, rule in enumerate(rich_rules.stdout.strip().split("\n")):
                if rule.strip():
                    rules.append({
                        "id": i + 1,
                        "zone": zone,
                        "type": "rich-rule",
                        "value": rule.strip()
                    })
    
    except Exception as e:
        pass
    
    return rules


def list_rules(firewall: str) -> dict:
    """List all firewall rules."""
    result = {
        "success": True,
        "action": "list",
        "firewall": firewall,
        "timestamp": datetime.now().isoformat(),
        "rules": []
    }
    
    if firewall == "iptables":
        result["rules"] = get_iptables_rules()
    elif firewall == "ufw":
        result["rules"] = get_ufw_rules()
    elif firewall == "firewalld":
        result["rules"] = get_firewalld_rules()
    
    result["count"] = len(result["rules"])
    return result


def add_rule(args: argparse.Namespace, firewall: str) -> dict:
    """Add a firewall rule."""
    result = {
        "success": False,
        "action": "add",
        "firewall": firewall,
        "timestamp": datetime.now().isoformat()
    }
    
    if not args.rule and not args.port:
        result["error"] = "Either --rule or --port must be specified"
        return result
    
    cmd = []
    if firewall == "iptables":
        chain = "INPUT" if args.direction == "in" else "OUTPUT"
        cmd = ["iptables", "-A", chain]
        
        if args.protocol:
            cmd.extend(["-p", args.protocol])
        if args.ip:
            cmd.extend(["-s", args.ip])
        if args.port:
            cmd.extend(["--dport", str(args.port)])
        if args.interface:
            cmd.extend(["-i", args.interface])
        
        cmd.extend(["-j", "ACCEPT"])
        
        if args.comment:
            cmd.extend(["-m", "comment", "--comment", args.comment])
    
    elif firewall == "ufw":
        if args.rule:
            cmd = ["ufw"] + args.rule.split()
        elif args.port:
            cmd = ["ufw", "allow", f"{args.port}/{args.protocol}"]
            if args.comment:
                cmd.extend(["comment", args.comment])
    
    elif firewall == "firewalld":
        if args.port:
            cmd = ["firewall-cmd", "--add-port", f"{args.port}/{args.protocol}"]
            if args.comment:
                cmd.extend(["--comment", args.comment])
        elif args.rule:
            cmd = ["firewall-cmd", "--add-rich-rule", args.rule]
    
    result["command"] = " ".join(cmd)
    
    if args.dry_run or args.simulate:
        result["success"] = True
        result["dry_run"] = True
    else:
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            result["success"] = True
        except subprocess.CalledProcessError as e:
            result["error"] = e.stderr or str(e)
        except Exception as e:
            result["error"] = str(e)
    
    return result


def remove_rule(args: argparse.Namespace, firewall: str) -> dict:
    """Remove a firewall rule."""
    result = {
        "success": False,
        "action": "remove",
        "firewall": firewall,
        "timestamp": datetime.now().isoformat()
    }
    
    if not args.rule_id:
        result["error"] = "Rule ID (--rule-id) must be specified"
        return result
    
    cmd = []
    if firewall == "iptables":
        cmd = ["iptables", "-D", "INPUT", str(args.rule_id)]
    elif firewall == "ufw":
        cmd = ["ufw", "delete", str(args.rule_id)]
    elif firewall == "firewalld":
        cmd = ["firewall-cmd", "--remove-rich-rule", str(args.rule_id)]
    
    result["command"] = " ".join(cmd)
    
    if args.dry_run or args.simulate:
        result["success"] = True
        result["dry_run"] = True
    else:
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            result["success"] = True
        except subprocess.CalledProcessError as e:
            result["error"] = e.stderr or str(e)
        except Exception as e:
            result["error"] = str(e)
    
    return result


def block_ip(args: argparse.Namespace, firewall: str) -> dict:
    """Block an IP address."""
    result = {
        "success": False,
        "action": "block",
        "firewall": firewall,
        "timestamp": datetime.now().isoformat(),
        "blocked_ip": args.ip
    }
    
    if not args.ip:
        result["error"] = "IP address (--ip) must be specified"
        return result
    
    cmd = []
    if firewall == "iptables":
        chain = "INPUT" if args.direction == "in" else "OUTPUT"
        cmd = ["iptables", "-I", chain, "-s", args.ip, "-j", "DROP"]
        if args.comment:
            cmd.extend(["-m", "comment", "--comment", args.comment])
    
    elif firewall == "ufw":
        cmd = ["ufw", "deny", "from", args.ip]
        if args.comment:
            cmd.extend(["comment", args.comment])
    
    elif firewall == "firewalld":
        cmd = ["firewall-cmd", "--add-rich-rule", 
               f"rule family='ipv4' source address='{args.ip}' reject"]
    
    result["command"] = " ".join(cmd)
    
    if args.dry_run or args.simulate:
        result["success"] = True
        result["dry_run"] = True
    else:
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            result["success"] = True
        except subprocess.CalledProcessError as e:
            result["error"] = e.stderr or str(e)
        except Exception as e:
            result["error"] = str(e)
    
    return result


def allow_port(args: argparse.Namespace, firewall: str) -> dict:
    """Allow traffic on a port."""
    result = {
        "success": False,
        "action": "allow",
        "firewall": firewall,
        "timestamp": datetime.now().isoformat(),
        "allowed_port": args.port,
        "protocol": args.protocol
    }
    
    if not args.port:
        result["error"] = "Port number (--port) must be specified"
        return result
    
    cmd = []
    if firewall == "iptables":
        chain = "INPUT" if args.direction == "in" else "OUTPUT"
        cmd = ["iptables", "-A", chain, "-p", args.protocol, 
               "--dport", str(args.port), "-j", "ACCEPT"]
        if args.ip:
            cmd.extend(["-s", args.ip])
        if args.comment:
            cmd.extend(["-m", "comment", "--comment", args.comment])
    
    elif firewall == "ufw":
        cmd = ["ufw", "allow", f"{args.port}/{args.protocol}"]
        if args.ip:
            cmd = ["ufw", "allow", "from", args.ip, "to", "any", "port", str(args.port)]
        if args.comment:
            cmd.extend(["comment", args.comment])
    
    elif firewall == "firewalld":
        cmd = ["firewall-cmd", "--add-port", f"{args.port}/{args.protocol}"]
    
    result["command"] = " ".join(cmd)
    
    if args.dry_run or args.simulate:
        result["success"] = True
        result["dry_run"] = True
    else:
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            result["success"] = True
        except subprocess.CalledProcessError as e:
            result["error"] = e.stderr or str(e)
        except Exception as e:
            result["error"] = str(e)
    
    return result


def get_status(firewall: str) -> dict:
    """Get firewall status."""
    result = {
        "success": True,
        "action": "status",
        "firewall": firewall,
        "timestamp": datetime.now().isoformat(),
        "status": "unknown"
    }
    
    try:
        if firewall == "iptables":
            proc = subprocess.run(["iptables", "-L", "-n"], capture_output=True)
            result["status"] = "active" if proc.returncode == 0 else "inactive"
        
        elif firewall == "ufw":
            proc = subprocess.run(["ufw", "status"], capture_output=True, text=True)
            output = proc.stdout.lower()
            if "active" in output and "inactive" not in output:
                result["status"] = "active"
            else:
                result["status"] = "inactive"
            result["details"] = proc.stdout.strip()
        
        elif firewall == "firewalld":
            proc = subprocess.run(["firewall-cmd", "--state"], capture_output=True, text=True)
            result["status"] = "active" if "running" in proc.stdout else "inactive"
    
    except Exception as e:
        result["error"] = str(e)
        result["status"] = "error"
    
    return result


def export_rules(firewall: str, output_file: str = None) -> dict:
    """Export firewall rules."""
    result = {
        "success": False,
        "action": "export",
        "firewall": firewall,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        if firewall == "iptables":
            proc = subprocess.run(
                ["iptables-save"],
                capture_output=True,
                text=True
            )
            result["rules"] = proc.stdout
            result["format"] = "iptables-save"
        
        elif firewall == "ufw":
            # UFW stores rules in /etc/ufw/
            rules_file = Path("/etc/ufw/user.rules")
            if rules_file.exists():
                result["rules"] = rules_file.read_text()
            result["format"] = "ufw"
        
        elif firewall == "firewalld":
            # Export all zones
            zones_proc = subprocess.run(
                ["firewall-cmd", "--get-active-zones"],
                capture_output=True,
                text=True
            )
            result["zones"] = zones_proc.stdout.strip()
            result["format"] = "firewalld"
        
        result["success"] = True
        
        if output_file:
            Path(output_file).write_text(json.dumps(result, indent=2))
            result["output_file"] = output_file
    
    except Exception as e:
        result["error"] = str(e)
    
    return result


def simulate_operation(args: argparse.Namespace) -> dict:
    """Simulate firewall operation for testing."""
    return {
        "success": True,
        "action": args.action,
        "firewall": args.firewall if args.firewall != "auto" else "iptables",
        "timestamp": datetime.now().isoformat(),
        "dry_run": True,
        "command": f"Simulated: {args.action} operation",
        "rules": [
            {"id": 1, "rule": "Allow SSH (22/tcp)", "action": "allow"},
            {"id": 2, "rule": "Allow HTTP (80/tcp)", "action": "allow"},
            {"id": 3, "rule": "Allow HTTPS (443/tcp)", "action": "allow"},
            {"id": 4, "rule": "Deny from 10.0.0.100", "action": "deny"}
        ],
        "status": "active"
    }


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    # Detect firewall if auto
    firewall = args.firewall
    if firewall == "auto":
        firewall = detect_firewall()
    
    # Handle simulation
    if args.simulate:
        result = simulate_operation(args)
    else:
        # Execute action
        if args.action == "list":
            result = list_rules(firewall)
        elif args.action == "add":
            result = add_rule(args, firewall)
        elif args.action == "remove":
            result = remove_rule(args, firewall)
        elif args.action == "block":
            result = block_ip(args, firewall)
        elif args.action == "allow":
            result = allow_port(args, firewall)
        elif args.action == "status":
            result = get_status(firewall)
        elif args.action == "export":
            result = export_rules(firewall, args.output)
        elif args.action == "import":
            result = {"success": False, "error": "Import not yet implemented"}
        else:
            result = {"success": False, "error": f"Unknown action: {args.action}"}
    
    # Output JSON
    output_json = json.dumps(result, indent=2)
    print(output_json)
    
    # Write to file if specified
    if args.output and args.action != "export":
        output_path = Path(args.output)
        output_path.write_text(output_json)
    
    return 0 if result.get("success", False) else 1


if __name__ == "__main__":
    sys.exit(main())