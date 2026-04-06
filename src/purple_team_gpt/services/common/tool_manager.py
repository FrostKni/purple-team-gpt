"""
Tool Manager - Auto-installation and management of security tools.

This module provides automatic tool installation, version checking,
and management for both Red and Blue agents running on bare metal systems.
"""

import asyncio
import logging
import shutil
import subprocess
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ToolStatus(str, Enum):
    """Status of a tool installation."""
    INSTALLED = "installed"
    MISSING = "missing"
    OUTDATED = "outdated"
    ERROR = "error"
    INSTALLING = "installing"


@dataclass
class ToolInfo:
    """Information about a security tool."""
    name: str
    category: str
    description: str
    check_command: str
    install_command: str
    update_command: Optional[str] = None
    version_regex: str = r"(\d+\.\d+\.?\d*)"
    dependencies: List[str] = field(default_factory=list)
    requires_root: bool = True
    platforms: List[str] = field(default_factory=lambda: ["linux"])
    
    # Runtime info
    installed_version: Optional[str] = None
    status: ToolStatus = ToolStatus.MISSING
    last_checked: Optional[str] = None
    error_message: Optional[str] = None


# =============================================================================
# RED TEAM TOOLS (Offensive)
# =============================================================================

RED_TEAM_TOOLS: Dict[str, ToolInfo] = {
    # Network Scanning
    "nmap": ToolInfo(
        name="nmap",
        category="scanning",
        description="Network discovery and security auditing",
        check_command="nmap --version",
        install_command="apt install -y nmap",
        update_command="apt install --only-upgrade nmap",
    ),
    "masscan": ToolInfo(
        name="masscan",
        category="scanning",
        description="Fast TCP port scanner",
        check_command="masscan --version",
        install_command="apt install -y masscan",
    ),
    "rustscan": ToolInfo(
        name="rustscan",
        category="scanning",
        description="Fast modern port scanner",
        check_command="rustscan --version",
        install_command="curl -L https://github.com/RustScan/RustScan/releases/latest/download/rustscan_$(uname -m).deb -o /tmp/rustscan.deb && dpkg -i /tmp/rustscan.deb",
    ),
    
    # Web Scanning
    "nikto": ToolInfo(
        name="nikto",
        category="web",
        description="Web server scanner",
        check_command="nikto -Version",
        install_command="apt install -y nikto",
    ),
    "whatweb": ToolInfo(
        name="whatweb",
        category="web",
        description="Web scanner to identify websites",
        check_command="whatweb --version",
        install_command="apt install -y whatweb",
    ),
    "wpscan": ToolInfo(
        name="wpscan",
        category="web",
        description="WordPress security scanner",
        check_command="wpscan --version",
        install_command="gem install wpscan",
    ),
    "nuclei": ToolInfo(
        name="nuclei",
        category="web",
        description="Fast vulnerability scanner",
        check_command="nuclei --version",
        install_command="go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
    ),
    
    # Directory Enumeration
    "gobuster": ToolInfo(
        name="gobuster",
        category="enumeration",
        description="Directory/file/DNS busting tool",
        check_command="gobuster version",
        install_command="apt install -y gobuster",
    ),
    "ffuf": ToolInfo(
        name="ffuf",
        category="enumeration",
        description="Fast web fuzzer",
        check_command="ffuf -V",
        install_command="apt install -y ffuf",
    ),
    "dirsearch": ToolInfo(
        name="dirsearch",
        category="enumeration",
        description="Web path scanner",
        check_command="dirsearch --version 2>/dev/null || python3 -c 'import dirsearch' 2>/dev/null",
        install_command="pip3 install dirsearch",
    ),
    
    # Vulnerability Scanning
    "sqlmap": ToolInfo(
        name="sqlmap",
        category="vulnerability",
        description="SQL injection tool",
        check_command="sqlmap --version",
        install_command="apt install -y sqlmap",
    ),
    "nuclei-templates": ToolInfo(
        name="nuclei-templates",
        category="vulnerability",
        description="Community vulnerability templates",
        check_command="nuclei -tl 2>/dev/null | head -1",
        install_command="nuclei -update-templates",
    ),
    
    # Password Attacks
    "hydra": ToolInfo(
        name="hydra",
        category="password",
        description="Network logon cracker",
        check_command="hydra -h 2>&1 | head -1",
        install_command="apt install -y hydra",
    ),
    "john": ToolInfo(
        name="john",
        category="password",
        description="Password cracker",
        check_command="john --list=formats 2>/dev/null | head -1",
        install_command="apt install -y john",
    ),
    "hashcat": ToolInfo(
        name="hashcat",
        category="password",
        description="GPU-accelerated password recovery",
        check_command="hashcat --version",
        install_command="apt install -y hashcat",
    ),
    "wordlists": ToolInfo(
        name="wordlists",
        category="password",
        description="Password wordlists (rockyou, etc)",
        check_command="test -f /usr/share/wordlists/rockyou.txt",
        install_command="apt install -y wordlists && gunzip /usr/share/wordlists/rockyou.txt.gz",
    ),
    
    # Exploitation
    "metasploit": ToolInfo(
        name="metasploit",
        category="exploitation",
        description="Metasploit Framework",
        check_command="msfconsole --version",
        install_command="apt install -y metasploit-framework",
    ),
    "searchsploit": ToolInfo(
        name="searchsploit",
        category="exploitation",
        description="Exploit Database searcher",
        check_command="searchsploit -V",
        install_command="apt install -y exploitdb",
    ),
    
    # Network Attacks
    "responder": ToolInfo(
        name="responder",
        category="network",
        description="LLMNR/NBT-NS/MDNS poisoner",
        check_command="responder --version 2>&1 | head -1",
        install_command="apt install -y responder",
    ),
    "ettercap": ToolInfo(
        name="ettercap",
        category="network",
        description="Network security toolkit",
        check_command="ettercap --version",
        install_command="apt install -y ettercap-graphical",
    ),
    "bettercap": ToolInfo(
        name="bettercap",
        category="network",
        description="Network attack and monitoring",
        check_command="bettercap --version",
        install_command="apt install -y bettercap",
    ),
    
    # Active Directory
    "crackmapexec": ToolInfo(
        name="crackmapexec",
        category="activedirectory",
        description="Swiss Army knife for AD",
        check_command="crackmapexec --version",
        install_command="pip3 install crackmapexec",
    ),
    "impacket": ToolInfo(
        name="impacket",
        category="activedirectory",
        description="Network protocol toolkit",
        check_command="python3 -c 'import impacket' 2>/dev/null && echo ok",
        install_command="pip3 install impacket",
    ),
    "bloodhound": ToolInfo(
        name="bloodhound",
        category="activedirectory",
        description="AD relationship analysis",
        check_command="bloodhound --version 2>/dev/null || which bloodhound",
        install_command="apt install -y bloodhound",
    ),
    "kerbrute": ToolInfo(
        name="kerbrute",
        category="activedirectory",
        description="Kerberos brute forcer",
        check_command="kerbrute version 2>/dev/null || which kerbrute",
        install_command="go install github.com/ropnop/kerbrute@latest",
    ),
    
    # OSINT
    "amass": ToolInfo(
        name="amass",
        category="osint",
        description="Attack surface mapping",
        check_command="amass -version",
        install_command="apt install -y amass",
    ),
    "subfinder": ToolInfo(
        name="subfinder",
        category="osint",
        description="Subdomain discovery",
        check_command="subfinder -version",
        install_command="go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
    ),
    "theharvester": ToolInfo(
        name="theharvester",
        category="osint",
        description="Email and subdomain gathering",
        check_command="theHarvester --version 2>/dev/null || which theHarvester",
        install_command="pip3 install theHarvester",
    ),
    
    # Wireless
    "aircrack-ng": ToolInfo(
        name="aircrack-ng",
        category="wireless",
        description="WiFi security auditing",
        check_command="aircrack-ng --help | head -1",
        install_command="apt install -y aircrack-ng",
    ),
    "wifite": ToolInfo(
        name="wifite",
        category="wireless",
        description="Wireless attack tool",
        check_command="wifite --help 2>&1 | head -1",
        install_command="apt install -y wifite",
    ),
    
    # Reverse Engineering
    "radare2": ToolInfo(
        name="radare2",
        category="reversing",
        description="Reverse engineering framework",
        check_command="r2 -v",
        install_command="apt install -y radare2",
    ),
    "ghidra": ToolInfo(
        name="ghidra",
        category="reversing",
        description="NSA reverse engineering tool",
        check_command="which ghidraRun",
        install_command="apt install -y ghidra",
    ),
    
    # Misc
    "curl": ToolInfo(
        name="curl",
        category="misc",
        description="Data transfer tool",
        check_command="curl --version",
        install_command="apt install -y curl",
        requires_root=False,
    ),
    "wget": ToolInfo(
        name="wget",
        category="misc",
        description="Network downloader",
        check_command="wget --version",
        install_command="apt install -y wget",
        requires_root=False,
    ),
    "netcat": ToolInfo(
        name="netcat",
        category="misc",
        description="Networking utility",
        check_command="nc -h 2>&1 | head -1",
        install_command="apt install -y netcat",
    ),
    "socat": ToolInfo(
        name="socat",
        category="misc",
        description="Multipurpose relay",
        check_command="socat -V",
        install_command="apt install -y socat",
    ),
}


# =============================================================================
# BLUE TEAM TOOLS (Defensive)
# =============================================================================

BLUE_TEAM_TOOLS: Dict[str, ToolInfo] = {
    # Firewall & Network Security
    "iptables": ToolInfo(
        name="iptables",
        category="firewall",
        description="Linux firewall",
        check_command="iptables --version",
        install_command="apt install -y iptables",
    ),
    "ufw": ToolInfo(
        name="ufw",
        category="firewall",
        description="Uncomplicated Firewall",
        check_command="ufw --version",
        install_command="apt install -y ufw",
    ),
    "nftables": ToolInfo(
        name="nftables",
        category="firewall",
        description="Netfilter userspace tool",
        check_command="nft --version",
        install_command="apt install -y nftables",
    ),
    
    # Intrusion Detection
    "suricata": ToolInfo(
        name="suricata",
        category="ids",
        description="Network IDS/IPS",
        check_command="suricata --build-info | head -1",
        install_command="apt install -y suricata",
    ),
    "zeek": ToolInfo(
        name="zeek",
        category="ids",
        description="Network security monitor",
        check_command="zeek --version",
        install_command="apt install -y zeek",
    ),
    "snort": ToolInfo(
        name="snort",
        category="ids",
        description="Network IDS",
        check_command="snort -V",
        install_command="apt install -y snort",
    ),
    "ossec": ToolInfo(
        name="ossec",
        category="hids",
        description="Host-based IDS",
        check_command="test -f /var/ossec/bin/ossec-control",
        install_command="apt install -y ossec-hids-server",
    ),
    "wazuh": ToolInfo(
        name="wazuh",
        category="hids",
        description="Security monitoring",
        check_command="test -f /var/ossec/bin/wazuh-control",
        install_command="apt install -y wazuh-manager",
    ),
    
    # Log Analysis
    "logwatch": ToolInfo(
        name="logwatch",
        category="logging",
        description="Log analysis tool",
        check_command="logwatch --help 2>&1 | head -1",
        install_command="apt install -y logwatch",
    ),
    "logstash": ToolInfo(
        name="logstash",
        category="logging",
        description="Log processing pipeline",
        check_command="logstash --version 2>/dev/null || test -f /usr/share/logstash/bin/logstash",
        install_command="apt install -y logstash",
    ),
    "filebeat": ToolInfo(
        name="filebeat",
        category="logging",
        description="Log shipper",
        check_command="filebeat version",
        install_command="apt install -y filebeat",
    ),
    
    # Malware Detection
    "rkhunter": ToolInfo(
        name="rkhunter",
        category="malware",
        description="Rootkit hunter",
        check_command="rkhunter --versioncheck 2>&1 | grep version",
        install_command="apt install -y rkhunter",
    ),
    "chkrootkit": ToolInfo(
        name="chkrootkit",
        category="malware",
        description="Rootkit checker",
        check_command="chkrootkit -V 2>&1 | head -1",
        install_command="apt install -y chkrootkit",
    ),
    "clamav": ToolInfo(
        name="clamav",
        category="malware",
        description="Antivirus toolkit",
        check_command="clamscan --version",
        install_command="apt install -y clamav clamav-daemon",
    ),
    "clamtk": ToolInfo(
        name="clamtk",
        category="malware",
        description="ClamAV GUI frontend",
        check_command="which clamtk",
        install_command="apt install -y clamtk",
    ),
    
    # Intrusion Prevention
    "fail2ban": ToolInfo(
        name="fail2ban",
        category="prevention",
        description="Ban IPs that show malicious signs",
        check_command="fail2ban-client -V 2>&1 | head -1",
        install_command="apt install -y fail2ban",
    ),
    "crowdsec": ToolInfo(
        name="crowdsec",
        category="prevention",
        description="Collaborative threat intelligence",
        check_command="cscli version",
        install_command="apt install -y crowdsec",
    ),
    "psad": ToolInfo(
        name="psad",
        category="prevention",
        description="Port scan detector",
        check_command="psad --Version",
        install_command="apt install -y psad",
    ),
    
    # System Auditing
    "auditd": ToolInfo(
        name="auditd",
        category="audit",
        description="Linux auditing system",
        check_command="auditd --version",
        install_command="apt install -y auditd audispd-plugins",
    ),
    "aide": ToolInfo(
        name="aide",
        category="audit",
        description="File integrity checker",
        check_command="aide --version",
        install_command="apt install -y aide",
    ),
    "osquery": ToolInfo(
        name="osquery",
        category="audit",
        description="OS instrumentation framework",
        check_command="osqueryd --version",
        install_command="apt install -y osquery",
    ),
    
    # Network Monitoring
    "tcpdump": ToolInfo(
        name="tcpdump",
        category="monitoring",
        description="Packet analyzer",
        check_command="tcpdump --version",
        install_command="apt install -y tcpdump",
    ),
    "tshark": ToolInfo(
        name="tshark",
        category="monitoring",
        description="Terminal Wireshark",
        check_command="tshark --version",
        install_command="apt install -y tshark",
    ),
    "iftop": ToolInfo(
        name="iftop",
        category="monitoring",
        description="Network bandwidth monitor",
        check_command="iftop -v 2>&1 | head -1",
        install_command="apt install -y iftop",
    ),
    "nethogs": ToolInfo(
        name="nethogs",
        category="monitoring",
        description="Network bandwidth per process",
        check_command="nethogs -V",
        install_command="apt install -y nethogs",
    ),
    "ss": ToolInfo(
        name="ss",
        category="monitoring",
        description="Socket statistics",
        check_command="ss -v 2>&1 | head -1",
        install_command="apt install -y iproute2",
    ),
    
    # Process Monitoring
    "htop": ToolInfo(
        name="htop",
        category="monitoring",
        description="Interactive process viewer",
        check_command="htop --version",
        install_command="apt install -y htop",
        requires_root=False,
    ),
    "lsof": ToolInfo(
        name="lsof",
        category="monitoring",
        description="List open files",
        check_command="lsof -v 2>&1 | head -1",
        install_command="apt install -y lsof",
    ),
    "strace": ToolInfo(
        name="strace",
        category="monitoring",
        description="System call tracer",
        check_command="strace -V",
        install_command="apt install -y strace",
    ),
    
    # SIEM/Analysis
    "elasticsearch": ToolInfo(
        name="elasticsearch",
        category="siem",
        description="Search and analytics engine",
        check_command="curl -s localhost:9200 2>/dev/null | grep -o '\"number\" : \"[^\"]*\"'",
        install_command="apt install -y elasticsearch",
    ),
    "kibana": ToolInfo(
        name="kibana",
        category="siem",
        description="Visualization platform",
        check_command="test -f /usr/share/kibana/bin/kibana",
        install_command="apt install -y kibana",
    ),
    
    # Forensics
    "volatility": ToolInfo(
        name="volatility",
        category="forensics",
        description="Memory forensics framework",
        check_command="volatility --version 2>/dev/null || python3 -c 'import volatility3'",
        install_command="pip3 install volatility3",
    ),
    "autopsy": ToolInfo(
        name="autopsy",
        category="forensics",
        description="Digital forensics platform",
        check_command="which autopsy",
        install_command="apt install -y autopsy",
    ),
    "sleuthkit": ToolInfo(
        name="sleuthkit",
        category="forensics",
        description="Forensic toolkit",
        check_command="fls -V",
        install_command="apt install -y sleuthkit",
    ),
    
    # Hardening
    "lynis": ToolInfo(
        name="lynis",
        category="hardening",
        description="Security auditing tool",
        check_command="lynis show version",
        install_command="apt install -y lynis",
    ),
    "tiger": ToolInfo(
        name="tiger",
        category="hardening",
        description="Security auditor",
        check_command="tiger -V 2>&1 | head -1",
        install_command="apt install -y tiger",
    ),
}


class ToolManager:
    """Manages security tool installation and status."""
    
    def __init__(
        self,
        agent_type: str,
        auto_install: bool = True,
        update_on_start: bool = False,
        custom_tools: Optional[Dict[str, ToolInfo]] = None,
    ):
        """Initialize the Tool Manager.
        
        Args:
            agent_type: 'red' or 'blue'
            auto_install: Automatically install missing tools
            update_on_start: Update tools on startup
            custom_tools: Additional custom tools
        """
        self.agent_type = agent_type
        self.auto_install = auto_install
        self.update_on_start = update_on_start
        
        # Load tools for this agent type
        if agent_type == "red":
            self.tools = RED_TEAM_TOOLS.copy()
        elif agent_type == "blue":
            self.tools = BLUE_TEAM_TOOLS.copy()
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        # Add custom tools
        if custom_tools:
            self.tools.update(custom_tools)
        
        # Status cache
        self._status_cache: Dict[str, ToolStatus] = {}
        
    async def check_tool(self, tool_name: str) -> Tuple[ToolStatus, Optional[str]]:
        """Check if a tool is installed and get version.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tuple of (status, version)
        """
        if tool_name not in self.tools:
            return ToolStatus.ERROR, None
            
        tool = self.tools[tool_name]
        
        try:
            # Run check command
            result = await self._run_command(
                tool.check_command,
                timeout=10,
                require_root=False,
            )
            
            if result["exit_code"] == 0:
                # Extract version
                version = None
                if tool.version_regex:
                    match = re.search(tool.version_regex, result["stdout"])
                    if match:
                        version = match.group(1)
                
                tool.installed_version = version
                tool.status = ToolStatus.INSTALLED
                self._status_cache[tool_name] = ToolStatus.INSTALLED
                
                return ToolStatus.INSTALLED, version
            else:
                tool.status = ToolStatus.MISSING
                self._status_cache[tool_name] = ToolStatus.MISSING
                return ToolStatus.MISSING, None
                
        except Exception as e:
            logger.error(f"Error checking tool {tool_name}: {e}")
            tool.status = ToolStatus.ERROR
            tool.error_message = str(e)
            self._status_cache[tool_name] = ToolStatus.ERROR
            return ToolStatus.ERROR, None
    
    async def install_tool(self, tool_name: str) -> Tuple[bool, str]:
        """Install a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tuple of (success, message)
        """
        if tool_name not in self.tools:
            return False, f"Unknown tool: {tool_name}"
            
        tool = self.tools[tool_name]
        
        # Check if already installed
        status, version = await self.check_tool(tool_name)
        if status == ToolStatus.INSTALLED:
            return True, f"Tool {tool_name} already installed (v{version})"
        
        logger.info(f"Installing tool: {tool_name}")
        tool.status = ToolStatus.INSTALLING
        
        try:
            # Install dependencies first
            if tool.dependencies:
                for dep in tool.dependencies:
                    dep_status, _ = await self.check_tool(dep)
                    if dep_status != ToolStatus.INSTALLED:
                        success, msg = await self.install_tool(dep)
                        if not success:
                            return False, f"Failed to install dependency {dep}: {msg}"
            
            # Run install command
            result = await self._run_command(
                tool.install_command,
                timeout=300,  # 5 minutes for installation
                require_root=tool.requires_root,
            )
            
            if result["exit_code"] == 0:
                # Verify installation
                status, version = await self.check_tool(tool_name)
                if status == ToolStatus.INSTALLED:
                    logger.info(f"Successfully installed {tool_name} (v{version})")
                    return True, f"Successfully installed {tool_name} (v{version})"
                else:
                    return False, f"Installation completed but verification failed"
            else:
                error = result["stderr"] or result["stdout"]
                tool.status = ToolStatus.ERROR
                tool.error_message = error
                return False, f"Installation failed: {error}"
                
        except Exception as e:
            logger.error(f"Error installing tool {tool_name}: {e}")
            tool.status = ToolStatus.ERROR
            tool.error_message = str(e)
            return False, str(e)
    
    async def update_tool(self, tool_name: str) -> Tuple[bool, str]:
        """Update a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tuple of (success, message)
        """
        if tool_name not in self.tools:
            return False, f"Unknown tool: {tool_name}"
            
        tool = self.tools[tool_name]
        
        if not tool.update_command:
            return False, f"No update command defined for {tool_name}"
        
        logger.info(f"Updating tool: {tool_name}")
        
        try:
            result = await self._run_command(
                tool.update_command,
                timeout=300,
                require_root=tool.requires_root,
            )
            
            if result["exit_code"] == 0:
                # Check new version
                status, version = await self.check_tool(tool_name)
                return True, f"Updated {tool_name} to v{version}"
            else:
                return False, f"Update failed: {result['stderr']}"
                
        except Exception as e:
            return False, str(e)
    
    async def ensure_tool(self, tool_name: str) -> Tuple[bool, str]:
        """Ensure a tool is installed, install if missing.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tuple of (available, message)
        """
        status, version = await self.check_tool(tool_name)
        
        if status == ToolStatus.INSTALLED:
            return True, f"Tool {tool_name} ready (v{version})"
        
        if self.auto_install:
            success, msg = await self.install_tool(tool_name)
            return success, msg
        else:
            return False, f"Tool {tool_name} not installed and auto_install=False"
    
    async def check_all_tools(self) -> Dict[str, Tuple[ToolStatus, Optional[str]]]:
        """Check all tools status.
        
        Returns:
            Dict mapping tool name to (status, version)
        """
        results = {}
        
        # Run checks in parallel
        tasks = [self.check_tool(name) for name in self.tools]
        tool_names = list(self.tools.keys())
        
        check_results = await asyncio.gather(*tasks)
        
        for name, (status, version) in zip(tool_names, check_results):
            results[name] = (status, version)
            
        return results
    
    async def install_missing_tools(self) -> Dict[str, Tuple[bool, str]]:
        """Install all missing tools.
        
        Returns:
            Dict mapping tool name to (success, message)
        """
        results = {}
        
        # Check all tools first
        status = await self.check_all_tools()
        
        # Install missing ones
        for name, (tool_status, version) in status.items():
            if tool_status != ToolStatus.INSTALLED:
                success, msg = await self.install_tool(name)
                results[name] = (success, msg)
                
        return results
    
    def get_tool_info(self, tool_name: str) -> Optional[ToolInfo]:
        """Get information about a tool."""
        return self.tools.get(tool_name)
    
    def list_tools(self, category: Optional[str] = None) -> List[ToolInfo]:
        """List all tools, optionally filtered by category."""
        if category:
            return [t for t in self.tools.values() if t.category == category]
        return list(self.tools.values())
    
    def get_status_report(self) -> Dict[str, Any]:
        """Get a status report of all tools."""
        return {
            "agent_type": self.agent_type,
            "total_tools": len(self.tools),
            "installed": sum(1 for t in self.tools.values() if t.status == ToolStatus.INSTALLED),
            "missing": sum(1 for t in self.tools.values() if t.status == ToolStatus.MISSING),
            "error": sum(1 for t in self.tools.values() if t.status == ToolStatus.ERROR),
            "tools": {
                name: {
                    "status": tool.status.value,
                    "version": tool.installed_version,
                    "category": tool.category,
                    "description": tool.description,
                }
                for name, tool in self.tools.items()
            }
        }
    
    async def _run_command(
        self,
        command: str,
        timeout: int = 60,
        require_root: bool = True,
    ) -> Dict[str, Any]:
        """Run a shell command.
        
        Args:
            command: Shell command to run
            timeout: Timeout in seconds
            require_root: Whether to use sudo
            
        Returns:
            Dict with exit_code, stdout, stderr
        """
        # Add sudo if needed
        if require_root and not command.startswith("sudo"):
            command = f"sudo {command}"
        
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout
            )
            
            return {
                "exit_code": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
            }
            
        except asyncio.TimeoutError:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
            }
        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
            }


# =============================================================================
# Helper functions
# =============================================================================

async def check_system_requirements() -> Dict[str, bool]:
    """Check if system meets requirements for running agents.
    
    Returns:
        Dict of requirement name to status
    """
    requirements = {
        "python": shutil.which("python3") is not None,
        "pip": shutil.which("pip3") is not None,
        "sudo": shutil.which("sudo") is not None,
        "curl": shutil.which("curl") is not None,
        "git": shutil.which("git") is not None,
    }
    
    # Check for internet connectivity
    try:
        proc = await asyncio.create_subprocess_shell(
            "ping -c 1 -W 2 8.8.8.8",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        requirements["internet"] = proc.returncode == 0
    except:
        requirements["internet"] = False
    
    return requirements


def get_recommended_tools(agent_type: str, scenario: str) -> List[str]:
    """Get recommended tools for a scenario.
    
    Args:
        agent_type: 'red' or 'blue'
        scenario: Scenario type
        
    Returns:
        List of recommended tool names
    """
    scenarios = {
        "red": {
            "web_application": ["nmap", "nikto", "gobuster", "sqlmap", "ffuf", "nuclei"],
            "network": ["nmap", "masscan", "nuclei", "searchsploit"],
            "activedirectory": ["crackmapexec", "impacket", "bloodhound", "kerbrute"],
            "wireless": ["aircrack-ng", "wifite"],
            "password": ["hydra", "john", "hashcat"],
            "osint": ["amass", "subfinder", "theharvester"],
        },
        "blue": {
            "network_monitoring": ["suricata", "zeek", "tcpdump", "tshark"],
            "endpoint": ["wazuh", "auditd", "osquery", "aide"],
            "incident_response": ["volatility", "sleuthkit", "autopsy"],
            "hardening": ["lynis", "ufw", "fail2ban", "crowdsec"],
            "malware": ["clamav", "rkhunter", "chkrootkit"],
        }
    }
    
    return scenarios.get(agent_type, {}).get(scenario, [])