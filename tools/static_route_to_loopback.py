import re
import ipaddress

# Read file
with open("static_routes.txt") as f:
    lines = f.readlines()

loopback_counter = 1
output = []

for line in lines:
    line = line.strip()
    if not line.startswith("ip route"):
        continue

    # Match line like: ip route 192.168.1.0 255.255.255.0 192.168.15.1
    match = re.match(r"ip route (\d+\.\d+\.\d+\.\d+) (\d+\.\d+\.\d+\.\d+) (\d+\.\d+\.\d+\.\d+)", line)
    if not match:
        continue

    network_str = match.group(1)
    subnet_mask = match.group(2)

    # Convert to ip_network object using netmask
    try:
        network = ipaddress.IPv4Network(f"{network_str}/{subnet_mask}", strict=False)
        loopback_ip = str(list(network.hosts())[0])
    except ValueError:
        continue

    loopback_config = f"""
interface Loopback{loopback_counter}
 ip address {loopback_ip} {subnet_mask}
"""
    output.append(loopback_config.strip())
    loopback_counter += 1

print("\n\n".join(output))