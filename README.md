# Fast Ping - Advanced Network Scanner

A high-performance, feature-rich network scanning tool that performs rapid subnet-wide ping sweeps with comprehensive latency reporting and network analysis.

## Features

### Core Capabilities
- **Asynchronous concurrent pinging** - Scan entire subnets in seconds
- **Detailed latency statistics** - Average, min, max, median, and standard deviation
- **Packet loss tracking** - Monitor network reliability
- **Multi-subnet support** - Scan multiple networks in one command
- **IPv6 support** - Full support for both IPv4 and IPv6 networks

### Discovery & Analysis
- **Hostname resolution** - Reverse DNS lookup for discovered hosts
- **MAC address detection** - Identify devices via ARP (local subnet)
- **Vendor identification** - Recognize device manufacturers from MAC addresses
- **Port scanning** - Check if specific ports are open on alive hosts
- **TCP ping alternative** - Scan hosts that block ICMP packets

### Advanced Features
- **Multiple export formats** - JSON, CSV, XML, and Markdown
- **Baseline comparison** - Track network changes over time
- **Continuous monitoring** - Real-time network state tracking
- **Colored output** - Visual feedback for quick analysis
- **Flexible filtering** - Filter by latency, status, and more
- **Exclude lists** - Skip specific IPs during scanning
- **Comprehensive logging** - Track scan history

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd fast_ping

# Install dependencies
pip install -r requirements.txt

# Make the script executable (optional)
chmod +x fast_ping.py
```

## Requirements

- Python 3.7+
- tqdm (for progress bars)
- Root/sudo privileges (for ICMP ping on some systems)

## Quick Start

### Basic Usage

```bash
# Scan a single subnet
python3 fast_ping.py 192.168.1.0/24

# Scan with hostname resolution
python3 fast_ping.py 192.168.1.0/24 --resolve-hostnames

# Show only alive hosts
python3 fast_ping.py 192.168.1.0/24 --alive-only
```

## Usage Examples

### Discovery and Enumeration

```bash
# Full network discovery with all features
python3 fast_ping.py 192.168.1.0/24 \
    --resolve-hostnames \
    --get-mac \
    --scan-ports 22 80 443 3389 \
    --verbose

# Scan multiple subnets
python3 fast_ping.py 192.168.1.0/24 10.0.0.0/24 172.16.0.0/22

# IPv6 network scan
python3 fast_ping.py 2001:db8::/64 --resolve-hostnames
```

### Performance Tuning

```bash
# Increase concurrency for faster scans
python3 fast_ping.py 192.168.1.0/24 --concurrency 200

# Quick scan with fewer pings
python3 fast_ping.py 192.168.1.0/24 --count 3 --timeout 0.5

# Adjust ping intervals
python3 fast_ping.py 192.168.1.0/24 --count 10 --interval 0.1
```

### Filtering and Sorting

```bash
# Show only fast-responding hosts
python3 fast_ping.py 192.168.1.0/24 --latency-max 10 --alive-only

# Show only slow-responding hosts
python3 fast_ping.py 192.168.1.0/24 --latency-min 50

# Sort by latency
python3 fast_ping.py 192.168.1.0/24 --sort-by latency --alive-only

# Exclude specific IPs
python3 fast_ping.py 192.168.1.0/24 --exclude-file exclude_list.txt
```

### Export and Reporting

```bash
# Export to JSON
python3 fast_ping.py 192.168.1.0/24 --json scan_results.json

# Export to multiple formats
python3 fast_ping.py 192.168.1.0/24 \
    --json results.json \
    --csv results.csv \
    --xml results.xml \
    --markdown report.md

# Quiet mode for automation
python3 fast_ping.py 192.168.1.0/24 --quiet --json results.json
```

### Baseline and Monitoring

```bash
# Save a baseline scan
python3 fast_ping.py 192.168.1.0/24 \
    --resolve-hostnames \
    --save-baseline baseline.json

# Compare current state with baseline
python3 fast_ping.py 192.168.1.0/24 \
    --resolve-hostnames \
    --compare-baseline baseline.json

# Continuous monitoring (scan every 60 seconds)
python3 fast_ping.py 192.168.1.0/24 \
    --monitor \
    --monitor-interval 60 \
    --log-file network.log

# Long-term monitoring with all features
python3 fast_ping.py 192.168.1.0/24 \
    --monitor \
    --monitor-interval 300 \
    --resolve-hostnames \
    --alive-only \
    --log-file monitoring.log
```

### TCP Ping (for firewalled hosts)

```bash
# Use TCP ping instead of ICMP
python3 fast_ping.py 192.168.1.0/24 --tcp-ping

# TCP ping on custom port
python3 fast_ping.py 192.168.1.0/24 --tcp-ping --tcp-port 443

# Combine with port scanning
python3 fast_ping.py 192.168.1.0/24 \
    --tcp-ping \
    --scan-ports 22 80 443 3389 8080
```

## Command-Line Options

### Positional Arguments
```
subnets              IP subnet(s) to scan (e.g., 192.168.0.0/24)
```

### Ping Configuration
```
-c, --count N        Number of ping packets to send (default: 5)
-i, --interval SEC   Interval between pings in seconds (default: 0.2)
-W, --timeout SEC    Timeout for each ping in seconds (default: 1.0)
--concurrency N      Maximum concurrent operations (default: 100)
--tcp-ping           Use TCP ping instead of ICMP
--tcp-port PORT      Port for TCP ping (default: 80)
```

### Discovery Options
```
-r, --resolve-hostnames    Resolve hostnames via reverse DNS
--dns-timeout SEC          DNS resolution timeout (default: 2.0)
-m, --get-mac             Get MAC addresses (local subnet only)
--arp-timeout SEC         ARP lookup timeout (default: 2.0)
-p, --scan-ports PORT...  Scan specified ports on alive hosts
--port-timeout SEC        Port scan timeout per port (default: 1.0)
```

### Filtering Options
```
--alive-only          Show only hosts that responded
--latency-min MS      Show only hosts with latency >= threshold
--latency-max MS      Show only hosts with latency <= threshold
--exclude-file FILE   File containing IPs to exclude (one per line)
```

### Output Options
```
-q, --quiet           Suppress progress bar and detailed output
-v, --verbose         Show additional details
--no-color            Disable colored output
--sort-by FIELD       Sort results by: ip, latency, hostname (default: ip)
```

### Export Options
```
--json FILE           Export results to JSON file
--csv FILE            Export results to CSV file
--xml FILE            Export results to XML file
--markdown FILE       Export results to Markdown file
```

### Monitoring and Baseline
```
--save-baseline FILE        Save scan as baseline for future comparison
--compare-baseline FILE     Compare scan with saved baseline
--monitor                   Continuously monitor network
--monitor-interval SEC      Monitoring interval in seconds (default: 60)
--log-file FILE            Log scan results to file
```

## Output Interpretation

### Color Coding
The terminal output uses colors to quickly identify host status:
- **Green**: Fast response (<10ms) or host came up
- **Yellow**: Medium response (10-50ms) or host changed
- **Red**: Slow response (>=50ms) or host went down

### Result Table Columns
- **IP Address**: The scanned IP address
- **Hostname**: Resolved hostname (if --resolve-hostnames used)
- **Avg (ms)**: Average latency in milliseconds
- **Min/Max**: Minimum and maximum latency observed
- **Loss%**: Packet loss percentage
- **Ports**: Open ports discovered (if --scan-ports used)

### Verbose Mode
With `-v/--verbose`, additional information is displayed:
- Median latency
- Standard deviation
- MAC address and vendor (if --get-mac used)

## Use Cases

### Network Administration
- Quickly identify all active devices on a network
- Monitor network performance and latency
- Track devices coming online or going offline
- Identify unauthorized devices via MAC addresses

### DevOps & Infrastructure
- Pre-deployment network validation
- Continuous infrastructure monitoring
- Service availability checking with port scans
- Network change detection and alerting

### Security & Auditing
- Network topology discovery
- Asset inventory and tracking
- Detecting rogue devices
- Compliance reporting with export formats

### Troubleshooting
- Identify hosts with high latency or packet loss
- Compare current network state with known-good baseline
- Monitor network stability over time
- Verify connectivity to specific services

## File Formats

### Exclude List Format
Create a text file with one IP address per line:
```
# Comments start with #
192.168.1.1
192.168.1.254
10.0.0.1
```

### Export Formats

**JSON**: Machine-readable format with complete statistics
```json
{
  "timestamp": "2025-10-22T...",
  "total_scanned": 254,
  "alive_count": 12,
  "results": [...]
}
```

**CSV**: Spreadsheet-compatible format
```csv
ip,hostname,alive,avg_latency_ms,min_latency_ms,max_latency_ms,...
192.168.1.1,router.local,True,1.23,1.15,1.45,...
```

**XML**: Enterprise integration format
```xml
<?xml version='1.0' encoding='utf-8'?>
<scan timestamp="..." total_scanned="254" alive_count="12">
  <host>...</host>
</scan>
```

**Markdown**: Human-readable documentation format
```markdown
# Network Scan Results
**Timestamp:** 2025-10-22T...
| IP Address | Hostname | Avg Latency (ms) | ... |
|------------|----------|------------------|-----|
```

## Performance Tips

1. **Increase Concurrency**: For larger networks, increase `--concurrency` to 200-500
2. **Reduce Ping Count**: Use `--count 3` for faster scans (less accuracy)
3. **Adjust Timeouts**: Lower timeouts speed up scans but may miss slow hosts
4. **Use Filters**: `--alive-only` reduces output processing time
5. **Disable Features**: Skip DNS/MAC/port scanning if not needed

## Limitations

- **ICMP Permissions**: May require root/sudo for ICMP ping on some systems
- **ARP/MAC Detection**: Only works on local subnet
- **DNS Timeouts**: Slow DNS servers can impact scan time
- **Firewall Restrictions**: Some hosts may block ICMP (use --tcp-ping)
- **Port Scanning**: Large port lists significantly increase scan time

## Troubleshooting

### "Operation not permitted" error
- Run with sudo: `sudo python3 fast_ping.py ...`
- Or use TCP ping: `python3 fast_ping.py --tcp-ping ...`

### No results showing
- Check subnet notation (e.g., 192.168.1.0/24)
- Verify network connectivity
- Try with `--verbose` for debugging

### Slow scans
- Increase `--concurrency`
- Decrease `--count` or `--timeout`
- Skip optional features like DNS resolution

### Baseline comparison not working
- Ensure baseline file exists and is valid JSON
- Check file permissions

## Contributing

Contributions are welcome! Areas for improvement:
- Full OUI database integration for MAC vendor lookup
- Additional output formats
- More port scanning options
- Network topology visualization
- Performance optimizations

## License

[Specify your license here]

## Author

[Your information here]

## Version History

### v2.0.0 (Current)
- Complete rewrite with extensive new features
- Added CLI argument parser
- Enhanced statistics (min/max/median/stddev)
- Hostname resolution support
- MAC address detection
- Port scanning capabilities
- Multiple export formats (JSON, CSV, XML, Markdown)
- Baseline comparison
- Continuous monitoring mode
- Multi-subnet support
- IPv6 support
- Filtering and sorting options
- Colored terminal output
- TCP ping alternative
- Logging functionality

### v1.0.0 (Legacy)
- Basic async ping functionality
- Simple progress bar
- Average latency reporting
