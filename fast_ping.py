#!/usr/bin/env python3
"""
Fast Ping - Advanced Network Scanner
Rapid subnet-wide ping sweeps with comprehensive latency reporting and network analysis
"""

import ipaddress
import asyncio
import subprocess
import argparse
import json
import csv
import xml.etree.ElementTree as ET
import socket
import statistics
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path
from tqdm import tqdm
import re


# Color codes for terminal output
class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

    @staticmethod
    def disable():
        """Disable colors for non-terminal output"""
        Colors.GREEN = ''
        Colors.YELLOW = ''
        Colors.RED = ''
        Colors.BLUE = ''
        Colors.CYAN = ''
        Colors.MAGENTA = ''
        Colors.BOLD = ''
        Colors.RESET = ''


class PingResult:
    """Container for ping result data"""
    def __init__(self, ip: str, hostname: Optional[str] = None,
                 latencies: Optional[List[float]] = None,
                 packets_sent: int = 0, packets_received: int = 0,
                 mac_address: Optional[str] = None, mac_vendor: Optional[str] = None,
                 open_ports: Optional[List[int]] = None):
        self.ip = ip
        self.hostname = hostname
        self.latencies = latencies or []
        self.packets_sent = packets_sent
        self.packets_received = packets_received
        self.mac_address = mac_address
        self.mac_vendor = mac_vendor
        self.open_ports = open_ports or []

    @property
    def is_alive(self) -> bool:
        """Check if host responded to ping"""
        return len(self.latencies) > 0

    @property
    def packet_loss(self) -> float:
        """Calculate packet loss percentage"""
        if self.packets_sent == 0:
            return 0.0
        return ((self.packets_sent - self.packets_received) / self.packets_sent) * 100

    @property
    def avg_latency(self) -> Optional[float]:
        """Calculate average latency"""
        return statistics.mean(self.latencies) if self.latencies else None

    @property
    def min_latency(self) -> Optional[float]:
        """Get minimum latency"""
        return min(self.latencies) if self.latencies else None

    @property
    def max_latency(self) -> Optional[float]:
        """Get maximum latency"""
        return max(self.latencies) if self.latencies else None

    @property
    def median_latency(self) -> Optional[float]:
        """Calculate median latency"""
        return statistics.median(self.latencies) if self.latencies else None

    @property
    def stddev_latency(self) -> Optional[float]:
        """Calculate standard deviation of latency"""
        return statistics.stdev(self.latencies) if len(self.latencies) > 1 else None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON/CSV export"""
        return {
            'ip': self.ip,
            'hostname': self.hostname,
            'alive': self.is_alive,
            'avg_latency_ms': round(self.avg_latency, 2) if self.avg_latency else None,
            'min_latency_ms': round(self.min_latency, 2) if self.min_latency else None,
            'max_latency_ms': round(self.max_latency, 2) if self.max_latency else None,
            'median_latency_ms': round(self.median_latency, 2) if self.median_latency else None,
            'stddev_latency_ms': round(self.stddev_latency, 2) if self.stddev_latency else None,
            'packet_loss_pct': round(self.packet_loss, 2),
            'packets_sent': self.packets_sent,
            'packets_received': self.packets_received,
            'mac_address': self.mac_address,
            'mac_vendor': self.mac_vendor,
            'open_ports': self.open_ports
        }


async def tcp_ping(ip: str, port: int = 80, timeout: float = 1.0) -> Optional[float]:
    """
    Perform TCP ping by attempting to connect to a port

    :param ip: IP address to ping
    :param port: Port to connect to
    :param timeout: Connection timeout
    :return: Connection time in milliseconds or None if failed
    """
    try:
        start_time = asyncio.get_event_loop().time()
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=timeout
        )
        end_time = asyncio.get_event_loop().time()
        writer.close()
        await writer.wait_closed()
        return (end_time - start_time) * 1000  # Convert to ms
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
        return None


async def scan_port(ip: str, port: int, timeout: float = 1.0) -> bool:
    """
    Check if a specific port is open

    :param ip: IP address to scan
    :param port: Port number to check
    :param timeout: Connection timeout
    :return: True if port is open, False otherwise
    """
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return True
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
        return False


async def scan_ports(ip: str, ports: List[int], timeout: float = 1.0) -> List[int]:
    """
    Scan multiple ports on a host

    :param ip: IP address to scan
    :param ports: List of ports to check
    :param timeout: Connection timeout per port
    :return: List of open ports
    """
    tasks = [scan_port(ip, port, timeout) for port in ports]
    results = await asyncio.gather(*tasks)
    return [port for port, is_open in zip(ports, results) if is_open]


async def get_hostname(ip: str, timeout: float = 2.0) -> Optional[str]:
    """
    Resolve hostname for an IP address

    :param ip: IP address to resolve
    :param timeout: DNS resolution timeout
    :return: Hostname or None if resolution fails
    """
    try:
        loop = asyncio.get_event_loop()
        hostname, _, _ = await asyncio.wait_for(
            loop.run_in_executor(None, socket.gethostbyaddr, ip),
            timeout=timeout
        )
        return hostname
    except (socket.herror, socket.gaierror, asyncio.TimeoutError, OSError):
        return None


async def get_mac_address(ip: str, timeout: float = 2.0) -> Tuple[Optional[str], Optional[str]]:
    """
    Get MAC address using ARP (works only on local subnet)

    :param ip: IP address to query
    :param timeout: ARP timeout
    :return: Tuple of (MAC address, vendor) or (None, None)
    """
    try:
        # Try using 'ip neigh' command (Linux)
        proc = await asyncio.create_subprocess_exec(
            'ip', 'neigh', 'show', ip,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        output = stdout.decode('utf-8').strip()

        # Parse MAC address from output
        mac_match = re.search(r'([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})', output)
        if mac_match:
            mac = mac_match.group(0)
            # Try to get vendor (simplified - would need OUI database for full functionality)
            vendor = get_mac_vendor(mac)
            return mac, vendor

        # Try arp command as fallback
        proc = await asyncio.create_subprocess_exec(
            'arp', '-n', ip,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        output = stdout.decode('utf-8').strip()

        mac_match = re.search(r'([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})', output)
        if mac_match:
            mac = mac_match.group(0)
            vendor = get_mac_vendor(mac)
            return mac, vendor

        return None, None
    except (asyncio.TimeoutError, FileNotFoundError, OSError):
        return None, None


def get_mac_vendor(mac: str) -> Optional[str]:
    """
    Get vendor name from MAC address (simplified version)
    In a full implementation, this would query an OUI database

    :param mac: MAC address
    :return: Vendor name or None
    """
    # This is a simplified version. A full implementation would use a proper OUI database
    # such as the IEEE OUI list or a library like 'mac-vendor-lookup'
    oui_prefix = mac.replace(':', '').replace('-', '').upper()[:6]

    # Some common vendors (very limited list for demo)
    common_vendors = {
        '000C29': 'VMware',
        '005056': 'VMware',
        '001C42': 'Parallels',
        '080027': 'VirtualBox',
        'B827EB': 'Raspberry Pi',
        'DCA632': 'Raspberry Pi',
        '001122': 'Cisco',
        '00D0D3': 'Cisco',
    }

    return common_vendors.get(oui_prefix)


async def ping_icmp(ip: str, count: int = 5, interval: float = 0.2,
                    timeout: float = 1.0, sem: asyncio.Semaphore = None) -> PingResult:
    """
    Perform ICMP ping and collect detailed statistics

    :param ip: IP address to ping
    :param count: Number of ping packets to send
    :param interval: Interval between pings
    :param timeout: Timeout for each ping
    :param sem: Semaphore for rate limiting
    :return: PingResult object with statistics
    """
    if sem:
        await sem.acquire()

    try:
        # Determine ping command based on IP version
        ip_obj = ipaddress.ip_address(ip)
        ping_cmd = 'ping6' if ip_obj.version == 6 else 'ping'

        # Build ping command
        proc = await asyncio.create_subprocess_exec(
            ping_cmd, '-c', str(count), '-i', str(interval), '-W', str(int(timeout)), str(ip),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            output = stdout.decode('utf-8').strip()

            # Parse individual ping times
            latencies = []
            for line in output.split('\n'):
                if 'time=' in line:
                    time_match = re.search(r'time=([0-9.]+)', line)
                    if time_match:
                        latencies.append(float(time_match.group(1)))

            # Parse packets transmitted/received
            stats_match = re.search(r'(\d+) packets transmitted, (\d+) received', output)
            packets_sent = int(stats_match.group(1)) if stats_match else count
            packets_received = int(stats_match.group(2)) if stats_match else len(latencies)

            return PingResult(
                ip=str(ip),
                latencies=latencies,
                packets_sent=packets_sent,
                packets_received=packets_received
            )
        else:
            return PingResult(ip=str(ip), packets_sent=count, packets_received=0)

    finally:
        if sem:
            sem.release()


async def ping_tcp_method(ip: str, port: int = 80, count: int = 5,
                          interval: float = 0.2, timeout: float = 1.0,
                          sem: asyncio.Semaphore = None) -> PingResult:
    """
    Perform TCP-based ping (for hosts that block ICMP)

    :param ip: IP address to ping
    :param port: TCP port to connect to
    :param count: Number of connection attempts
    :param interval: Interval between attempts
    :param timeout: Timeout for each attempt
    :param sem: Semaphore for rate limiting
    :return: PingResult object with statistics
    """
    if sem:
        await sem.acquire()

    try:
        latencies = []
        for _ in range(count):
            latency = await tcp_ping(ip, port, timeout)
            if latency is not None:
                latencies.append(latency)
            await asyncio.sleep(interval)

        return PingResult(
            ip=str(ip),
            latencies=latencies,
            packets_sent=count,
            packets_received=len(latencies)
        )
    finally:
        if sem:
            sem.release()


async def comprehensive_scan(ip: str, args: argparse.Namespace,
                             sem: asyncio.Semaphore) -> PingResult:
    """
    Perform comprehensive scan of a host including ping, DNS, MAC, and port scan

    :param ip: IP address to scan
    :param args: Command-line arguments
    :param sem: Semaphore for rate limiting
    :return: Complete PingResult object
    """
    # Perform ping (ICMP or TCP based on arguments)
    if args.tcp_ping:
        result = await ping_tcp_method(
            ip, args.tcp_port, args.count, args.interval, args.timeout, sem
        )
    else:
        result = await ping_icmp(
            ip, args.count, args.interval, args.timeout, sem
        )

    # Only do additional scans if host is alive
    if result.is_alive:
        # Resolve hostname if requested
        if args.resolve_hostnames:
            result.hostname = await get_hostname(str(ip), args.dns_timeout)

        # Get MAC address if requested
        if args.get_mac:
            result.mac_address, result.mac_vendor = await get_mac_address(
                str(ip), args.arp_timeout
            )

        # Scan ports if requested
        if args.scan_ports:
            result.open_ports = await scan_ports(str(ip), args.scan_ports, args.port_timeout)

    return result


def load_exclude_list(file_path: str) -> Set[str]:
    """
    Load IP addresses to exclude from a file

    :param file_path: Path to exclude list file
    :return: Set of IP addresses to exclude
    """
    exclude_set = set()
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        # Validate IP address
                        ipaddress.ip_address(line)
                        exclude_set.add(line)
                    except ValueError:
                        print(f"Warning: Invalid IP address in exclude list: {line}", file=sys.stderr)
    except FileNotFoundError:
        print(f"Warning: Exclude list file not found: {file_path}", file=sys.stderr)

    return exclude_set


def filter_results(results: List[PingResult], args: argparse.Namespace) -> List[PingResult]:
    """
    Filter results based on command-line arguments

    :param results: List of ping results
    :param args: Command-line arguments
    :return: Filtered list of results
    """
    filtered = results

    # Filter alive only
    if args.alive_only:
        filtered = [r for r in filtered if r.is_alive]

    # Filter by latency thresholds
    if args.latency_min is not None:
        filtered = [r for r in filtered if r.avg_latency and r.avg_latency >= args.latency_min]

    if args.latency_max is not None:
        filtered = [r for r in filtered if r.avg_latency and r.avg_latency <= args.latency_max]

    return filtered


def sort_results(results: List[PingResult], sort_by: str) -> List[PingResult]:
    """
    Sort results by specified field

    :param results: List of ping results
    :param sort_by: Field to sort by (ip, latency, hostname)
    :return: Sorted list of results
    """
    if sort_by == 'latency':
        return sorted(results, key=lambda r: r.avg_latency if r.avg_latency else float('inf'))
    elif sort_by == 'hostname':
        return sorted(results, key=lambda r: r.hostname or r.ip)
    else:  # Default to IP
        return sorted(results, key=lambda r: ipaddress.ip_address(r.ip))


def get_latency_color(latency: Optional[float]) -> str:
    """
    Get color code based on latency value

    :param latency: Latency in milliseconds
    :return: ANSI color code
    """
    if latency is None:
        return Colors.RED
    elif latency < 10:
        return Colors.GREEN
    elif latency < 50:
        return Colors.YELLOW
    else:
        return Colors.RED


def print_results_table(results: List[PingResult], args: argparse.Namespace):
    """
    Print results in a formatted table

    :param results: List of ping results
    :param args: Command-line arguments
    """
    if not results:
        print("No results to display.")
        return

    # Header
    print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{'IP Address':<15} {'Hostname':<25} {'Avg (ms)':<10} {'Min/Max':<15} {'Loss%':<8} {'Ports':<10}{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}")

    # Results
    for result in results:
        if not result.is_alive and args.alive_only:
            continue

        color = get_latency_color(result.avg_latency)

        hostname = result.hostname[:23] + '..' if result.hostname and len(result.hostname) > 25 else (result.hostname or '-')
        avg_str = f"{result.avg_latency:.2f}" if result.avg_latency else "N/A"
        minmax_str = f"{result.min_latency:.1f}/{result.max_latency:.1f}" if result.min_latency else "N/A"
        loss_str = f"{result.packet_loss:.1f}%"
        ports_str = ','.join(map(str, result.open_ports[:3])) if result.open_ports else '-'
        if len(result.open_ports) > 3:
            ports_str += '...'

        print(f"{color}{result.ip:<15}{Colors.RESET} {hostname:<25} {color}{avg_str:<10}{Colors.RESET} "
              f"{minmax_str:<15} {loss_str:<8} {ports_str:<10}")

        # Show additional details if verbose
        if args.verbose and result.is_alive:
            if result.median_latency:
                print(f"  └─ Median: {result.median_latency:.2f}ms", end='')
            if result.stddev_latency:
                print(f", StdDev: {result.stddev_latency:.2f}ms", end='')
            if result.mac_address:
                vendor_str = f" ({result.mac_vendor})" if result.mac_vendor else ""
                print(f", MAC: {result.mac_address}{vendor_str}", end='')
            print()

    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")


def print_summary(results: List[PingResult], total_hosts: int):
    """
    Print summary statistics

    :param results: List of ping results
    :param total_hosts: Total number of hosts scanned
    """
    alive_results = [r for r in results if r.is_alive]
    alive_count = len(alive_results)
    dead_count = total_hosts - alive_count

    if alive_results:
        all_latencies = [r.avg_latency for r in alive_results if r.avg_latency]
        if all_latencies:
            overall_avg = statistics.mean(all_latencies)
            overall_min = min(all_latencies)
            overall_max = max(all_latencies)

            print(f"{Colors.BOLD}Summary Statistics:{Colors.RESET}")
            print(f"  Total hosts scanned: {total_hosts}")
            print(f"  Alive: {Colors.GREEN}{alive_count}{Colors.RESET} | Dead: {Colors.RED}{dead_count}{Colors.RESET}")
            print(f"  Average latency: {overall_avg:.2f}ms")
            print(f"  Latency range: {overall_min:.2f}ms - {overall_max:.2f}ms")

            # Count hosts by latency category
            fast = len([l for l in all_latencies if l < 10])
            medium = len([l for l in all_latencies if 10 <= l < 50])
            slow = len([l for l in all_latencies if l >= 50])

            print(f"  Response time distribution:")
            print(f"    {Colors.GREEN}Fast (<10ms): {fast}{Colors.RESET}")
            print(f"    {Colors.YELLOW}Medium (10-50ms): {medium}{Colors.RESET}")
            print(f"    {Colors.RED}Slow (>=50ms): {slow}{Colors.RESET}")
    else:
        print(f"{Colors.BOLD}Summary:{Colors.RESET} No alive hosts found out of {total_hosts} scanned.")


def export_json(results: List[PingResult], file_path: str, timestamp: str):
    """
    Export results to JSON format

    :param results: List of ping results
    :param file_path: Output file path
    :param timestamp: Scan timestamp
    """
    data = {
        'timestamp': timestamp,
        'total_scanned': len(results),
        'alive_count': len([r for r in results if r.is_alive]),
        'results': [r.to_dict() for r in results]
    }

    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Results exported to JSON: {file_path}")


def export_csv(results: List[PingResult], file_path: str):
    """
    Export results to CSV format

    :param results: List of ping results
    :param file_path: Output file path
    """
    if not results:
        return

    with open(file_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].to_dict().keys())
        writer.writeheader()
        for result in results:
            writer.writerow(result.to_dict())

    print(f"Results exported to CSV: {file_path}")


def export_xml(results: List[PingResult], file_path: str, timestamp: str):
    """
    Export results to XML format

    :param results: List of ping results
    :param file_path: Output file path
    :param timestamp: Scan timestamp
    """
    root = ET.Element('scan')
    root.set('timestamp', timestamp)
    root.set('total_scanned', str(len(results)))
    root.set('alive_count', str(len([r for r in results if r.is_alive])))

    for result in results:
        host = ET.SubElement(root, 'host')
        for key, value in result.to_dict().items():
            if value is not None:
                elem = ET.SubElement(host, key)
                elem.text = str(value)

    tree = ET.ElementTree(root)
    ET.indent(tree, space='  ')
    tree.write(file_path, encoding='utf-8', xml_declaration=True)

    print(f"Results exported to XML: {file_path}")


def export_markdown(results: List[PingResult], file_path: str, timestamp: str):
    """
    Export results to Markdown format

    :param results: List of ping results
    :param file_path: Output file path
    :param timestamp: Scan timestamp
    """
    with open(file_path, 'w') as f:
        f.write(f"# Network Scan Results\n\n")
        f.write(f"**Timestamp:** {timestamp}\n\n")
        f.write(f"**Total Scanned:** {len(results)}\n\n")
        f.write(f"**Alive Hosts:** {len([r for r in results if r.is_alive])}\n\n")

        f.write("## Results\n\n")
        f.write("| IP Address | Hostname | Avg Latency (ms) | Min/Max (ms) | Packet Loss | Open Ports |\n")
        f.write("|------------|----------|------------------|--------------|-------------|------------|\n")

        for result in results:
            if result.is_alive:
                hostname = result.hostname or '-'
                avg = f"{result.avg_latency:.2f}" if result.avg_latency else 'N/A'
                minmax = f"{result.min_latency:.2f}/{result.max_latency:.2f}" if result.min_latency else 'N/A'
                loss = f"{result.packet_loss:.1f}%"
                ports = ','.join(map(str, result.open_ports)) if result.open_ports else '-'

                f.write(f"| {result.ip} | {hostname} | {avg} | {minmax} | {loss} | {ports} |\n")

    print(f"Results exported to Markdown: {file_path}")


def save_baseline(results: List[PingResult], file_path: str):
    """
    Save scan results as a baseline for future comparison

    :param results: List of ping results
    :param file_path: Output file path
    """
    timestamp = datetime.now().isoformat()
    export_json(results, file_path, timestamp)
    print(f"Baseline saved: {file_path}")


def load_baseline(file_path: str) -> List[PingResult]:
    """
    Load baseline scan results

    :param file_path: Input file path
    :return: List of ping results from baseline
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        results = []
        for item in data.get('results', []):
            result = PingResult(
                ip=item['ip'],
                hostname=item.get('hostname'),
                latencies=[item.get('avg_latency_ms', 0)] if item.get('alive') else [],
                packets_sent=item.get('packets_sent', 0),
                packets_received=item.get('packets_received', 0),
                mac_address=item.get('mac_address'),
                mac_vendor=item.get('mac_vendor'),
                open_ports=item.get('open_ports', [])
            )
            results.append(result)

        return results
    except FileNotFoundError:
        print(f"Error: Baseline file not found: {file_path}", file=sys.stderr)
        return []
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in baseline file: {file_path}", file=sys.stderr)
        return []


def compare_with_baseline(current: List[PingResult], baseline: List[PingResult]):
    """
    Compare current scan results with baseline

    :param current: Current scan results
    :param baseline: Baseline scan results
    """
    baseline_dict = {r.ip: r for r in baseline}
    current_dict = {r.ip: r for r in current}

    # Find new, missing, and changed hosts
    new_hosts = []
    missing_hosts = []
    changed_hosts = []

    for ip, curr_result in current_dict.items():
        if ip not in baseline_dict:
            if curr_result.is_alive:
                new_hosts.append(curr_result)
        else:
            base_result = baseline_dict[ip]
            if curr_result.is_alive != base_result.is_alive:
                changed_hosts.append((curr_result, base_result))
            elif curr_result.is_alive and base_result.is_alive:
                if curr_result.avg_latency and base_result.avg_latency:
                    latency_change = abs(curr_result.avg_latency - base_result.avg_latency)
                    if latency_change > 10:  # More than 10ms difference
                        changed_hosts.append((curr_result, base_result))

    for ip, base_result in baseline_dict.items():
        if ip not in current_dict and base_result.is_alive:
            missing_hosts.append(base_result)

    # Print comparison
    print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}Baseline Comparison{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")

    if new_hosts:
        print(f"{Colors.GREEN}New hosts ({len(new_hosts)}):{Colors.RESET}")
        for host in new_hosts:
            print(f"  + {host.ip} (latency: {host.avg_latency:.2f}ms)")
        print()

    if missing_hosts:
        print(f"{Colors.RED}Missing hosts ({len(missing_hosts)}):{Colors.RESET}")
        for host in missing_hosts:
            print(f"  - {host.ip}")
        print()

    if changed_hosts:
        print(f"{Colors.YELLOW}Changed hosts ({len(changed_hosts)}):{Colors.RESET}")
        for curr, base in changed_hosts:
            if curr.is_alive != base.is_alive:
                status = "UP" if curr.is_alive else "DOWN"
                print(f"  ~ {curr.ip}: Now {status}")
            elif curr.avg_latency and base.avg_latency:
                change = curr.avg_latency - base.avg_latency
                direction = "increased" if change > 0 else "decreased"
                print(f"  ~ {curr.ip}: Latency {direction} by {abs(change):.2f}ms "
                      f"({base.avg_latency:.2f}ms -> {curr.avg_latency:.2f}ms)")
        print()

    if not new_hosts and not missing_hosts and not changed_hosts:
        print(f"{Colors.GREEN}No significant changes detected.{Colors.RESET}\n")


def log_scan(results: List[PingResult], log_file: str):
    """
    Append scan results to log file

    :param results: List of ping results
    :param log_file: Path to log file
    """
    timestamp = datetime.now().isoformat()
    alive_count = len([r for r in results if r.is_alive])

    log_entry = {
        'timestamp': timestamp,
        'total_scanned': len(results),
        'alive_count': alive_count,
        'alive_ips': [r.ip for r in results if r.is_alive]
    }

    # Create log file if it doesn't exist
    log_path = Path(log_file)
    if not log_path.exists():
        with open(log_file, 'w') as f:
            json.dump([log_entry], f, indent=2)
    else:
        # Append to existing log
        with open(log_file, 'r') as f:
            logs = json.load(f)
        logs.append(log_entry)
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)

    if not hasattr(log_scan, 'already_notified'):
        print(f"Scan logged to: {log_file}")
        log_scan.already_notified = True


async def scan_subnets(subnets: List[str], args: argparse.Namespace) -> List[PingResult]:
    """
    Scan multiple subnets

    :param subnets: List of subnet strings
    :param args: Command-line arguments
    :return: Combined list of ping results
    """
    all_results = []
    exclude_ips = set()

    # Load exclude list if specified
    if args.exclude_file:
        exclude_ips = load_exclude_list(args.exclude_file)

    for subnet_str in subnets:
        try:
            # Parse subnet
            network = ipaddress.ip_network(subnet_str, strict=False)
            hosts = list(network.hosts())

            # Filter excluded IPs
            hosts = [ip for ip in hosts if str(ip) not in exclude_ips]

            if not hosts:
                print(f"No hosts to scan in subnet {subnet_str}")
                continue

            print(f"\n{Colors.CYAN}Scanning subnet: {subnet_str} ({len(hosts)} hosts){Colors.RESET}")

            # Create semaphore for rate limiting
            sem = asyncio.Semaphore(args.concurrency)

            # Create tasks
            tasks = []
            with tqdm(total=len(hosts), desc=f'Scanning {subnet_str}',
                     disable=args.quiet, unit='host') as pbar:
                for ip in hosts:
                    task = asyncio.create_task(comprehensive_scan(str(ip), args, sem))
                    task.add_done_callback(lambda x: pbar.update())
                    tasks.append(task)

                # Wait for all tasks to complete
                results = await asyncio.gather(*tasks)

            all_results.extend(results)

        except ValueError as e:
            print(f"Error: Invalid subnet '{subnet_str}': {e}", file=sys.stderr)
            continue

    return all_results


async def continuous_monitoring(subnets: List[str], args: argparse.Namespace):
    """
    Continuously monitor network at specified intervals

    :param subnets: List of subnets to monitor
    :param args: Command-line arguments
    """
    iteration = 0
    previous_results = None

    try:
        while True:
            iteration += 1
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
            print(f"{Colors.BOLD}Monitoring Iteration #{iteration} - {timestamp}{Colors.RESET}")
            print(f"{Colors.BOLD}{'='*80}{Colors.RESET}")

            # Perform scan
            results = await scan_subnets(subnets, args)

            # Filter and sort results
            results = filter_results(results, args)
            results = sort_results(results, args.sort_by)

            # Display results
            if not args.quiet:
                print_results_table(results, args)
                print_summary(results, len(results))

            # Compare with previous iteration
            if previous_results:
                current_alive = set(r.ip for r in results if r.is_alive)
                previous_alive = set(r.ip for r in previous_results if r.is_alive)

                new_up = current_alive - previous_alive
                new_down = previous_alive - current_alive

                if new_up:
                    print(f"\n{Colors.GREEN}Hosts came UP:{Colors.RESET}")
                    for ip in sorted(new_up, key=lambda x: ipaddress.ip_address(x)):
                        print(f"  + {ip}")

                if new_down:
                    print(f"\n{Colors.RED}Hosts went DOWN:{Colors.RESET}")
                    for ip in sorted(new_down, key=lambda x: ipaddress.ip_address(x)):
                        print(f"  - {ip}")

            # Log if requested
            if args.log_file:
                log_scan(results, args.log_file)

            previous_results = results

            # Wait for next iteration
            print(f"\nNext scan in {args.monitor_interval} seconds... (Press Ctrl+C to stop)")
            await asyncio.sleep(args.monitor_interval)

    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Monitoring stopped by user.{Colors.RESET}")


def create_parser() -> argparse.ArgumentParser:
    """
    Create command-line argument parser

    :return: Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description='Fast Ping - Advanced network scanner with comprehensive reporting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic subnet scan
  %(prog)s 192.168.1.0/24

  # Scan with hostname resolution
  %(prog)s 192.168.1.0/24 --resolve-hostnames

  # Scan multiple subnets with port scanning
  %(prog)s 192.168.1.0/24 10.0.0.0/24 --scan-ports 22 80 443

  # Export results to JSON and CSV
  %(prog)s 192.168.1.0/24 --json results.json --csv results.csv

  # Continuous monitoring every 60 seconds
  %(prog)s 192.168.1.0/24 --monitor --interval 60

  # Compare with baseline
  %(prog)s 192.168.1.0/24 --compare-baseline baseline.json

  # Advanced scan with all features
  %(prog)s 192.168.1.0/24 --resolve-hostnames --get-mac --scan-ports 22 80 443 \\
           --concurrency 200 --json results.json --verbose
        """
    )

    # Positional arguments
    parser.add_argument('subnets', nargs='+',
                       help='IP subnet(s) to scan (e.g., 192.168.0.0/24)')

    # Ping configuration
    ping_group = parser.add_argument_group('Ping Configuration')
    ping_group.add_argument('-c', '--count', type=int, default=5,
                           help='Number of ping packets to send (default: 5)')
    ping_group.add_argument('-i', '--interval', type=float, default=0.2,
                           help='Interval between pings in seconds (default: 0.2)')
    ping_group.add_argument('-W', '--timeout', type=float, default=1.0,
                           help='Timeout for each ping in seconds (default: 1.0)')
    ping_group.add_argument('--concurrency', type=int, default=100,
                           help='Maximum concurrent operations (default: 100)')
    ping_group.add_argument('--tcp-ping', action='store_true',
                           help='Use TCP ping instead of ICMP (for firewalled hosts)')
    ping_group.add_argument('--tcp-port', type=int, default=80,
                           help='Port for TCP ping (default: 80)')

    # Discovery options
    discovery_group = parser.add_argument_group('Discovery Options')
    discovery_group.add_argument('-r', '--resolve-hostnames', action='store_true',
                                help='Resolve hostnames via reverse DNS')
    discovery_group.add_argument('--dns-timeout', type=float, default=2.0,
                                help='DNS resolution timeout (default: 2.0)')
    discovery_group.add_argument('-m', '--get-mac', action='store_true',
                                help='Get MAC addresses (local subnet only)')
    discovery_group.add_argument('--arp-timeout', type=float, default=2.0,
                                help='ARP lookup timeout (default: 2.0)')
    discovery_group.add_argument('-p', '--scan-ports', type=int, nargs='+', metavar='PORT',
                                help='Scan specified ports on alive hosts')
    discovery_group.add_argument('--port-timeout', type=float, default=1.0,
                                help='Port scan timeout per port (default: 1.0)')

    # Filtering options
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('--alive-only', action='store_true',
                             help='Show only hosts that responded')
    filter_group.add_argument('--latency-min', type=float, metavar='MS',
                             help='Show only hosts with latency >= threshold')
    filter_group.add_argument('--latency-max', type=float, metavar='MS',
                             help='Show only hosts with latency <= threshold')
    filter_group.add_argument('--exclude-file', type=str, metavar='FILE',
                             help='File containing IPs to exclude (one per line)')

    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument('-q', '--quiet', action='store_true',
                             help='Suppress progress bar and detailed output')
    output_group.add_argument('-v', '--verbose', action='store_true',
                             help='Show additional details')
    output_group.add_argument('--no-color', action='store_true',
                             help='Disable colored output')
    output_group.add_argument('--sort-by', choices=['ip', 'latency', 'hostname'],
                             default='ip', help='Sort results by field (default: ip)')

    # Export options
    export_group = parser.add_argument_group('Export Options')
    export_group.add_argument('--json', type=str, metavar='FILE',
                             help='Export results to JSON file')
    export_group.add_argument('--csv', type=str, metavar='FILE',
                             help='Export results to CSV file')
    export_group.add_argument('--xml', type=str, metavar='FILE',
                             help='Export results to XML file')
    export_group.add_argument('--markdown', type=str, metavar='FILE',
                             help='Export results to Markdown file')

    # Baseline and monitoring
    monitoring_group = parser.add_argument_group('Monitoring and Baseline')
    monitoring_group.add_argument('--save-baseline', type=str, metavar='FILE',
                                 help='Save scan as baseline for future comparison')
    monitoring_group.add_argument('--compare-baseline', type=str, metavar='FILE',
                                 help='Compare scan with saved baseline')
    monitoring_group.add_argument('--monitor', action='store_true',
                                 help='Continuously monitor network')
    monitoring_group.add_argument('--monitor-interval', type=int, default=60, metavar='SEC',
                                 help='Monitoring interval in seconds (default: 60)')
    monitoring_group.add_argument('--log-file', type=str, metavar='FILE',
                                 help='Log scan results to file')

    return parser


async def main():
    """
    Main function
    """
    parser = create_parser()
    args = parser.parse_args()

    # Disable colors if requested or if not a TTY
    if args.no_color or not sys.stdout.isatty():
        Colors.disable()

    # Validate inputs
    if args.count < 1:
        print("Error: Ping count must be at least 1", file=sys.stderr)
        sys.exit(1)

    if args.concurrency < 1:
        print("Error: Concurrency must be at least 1", file=sys.stderr)
        sys.exit(1)

    try:
        # Load baseline if comparison requested
        baseline = None
        if args.compare_baseline:
            baseline = load_baseline(args.compare_baseline)
            if not baseline:
                print("Error: Could not load baseline file", file=sys.stderr)
                sys.exit(1)

        # Run monitoring mode or single scan
        if args.monitor:
            await continuous_monitoring(args.subnets, args)
        else:
            # Perform scan
            results = await scan_subnets(args.subnets, args)

            # Filter and sort results
            results = filter_results(results, args)
            results = sort_results(results, args.sort_by)

            # Display results
            if not args.quiet:
                print_results_table(results, args)
                total_hosts = len(results)
                print_summary(results, total_hosts)

            # Compare with baseline if requested
            if baseline:
                compare_with_baseline(results, baseline)

            # Export results
            timestamp = datetime.now().isoformat()

            if args.json:
                export_json(results, args.json, timestamp)

            if args.csv:
                export_csv(results, args.csv)

            if args.xml:
                export_xml(results, args.xml, timestamp)

            if args.markdown:
                export_markdown(results, args.markdown, timestamp)

            # Save baseline if requested
            if args.save_baseline:
                save_baseline(results, args.save_baseline)

            # Log if requested
            if args.log_file:
                log_scan(results, args.log_file)

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Scan interrupted by user.{Colors.RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.RESET}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
