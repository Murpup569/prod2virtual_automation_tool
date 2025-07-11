import re
import ipaddress

# Read file
with open("show_ip_route.txt") as f:
    lines = f.readlines()

counter = 1
output = []

for line in lines:
    line = line.strip()
    if not line.startswith("B"):
        continue

    # Match line like: B        192.168.1.0/24 [200/0] via 192.168.1.1, 1d30h
    match = re.match(r"^B\s+(\d+\.\d+\.\d+\.\d+)/(\d+)", line)
    if not match:
        continue

    network_str = match.group(1)
    cidr = int(match.group(2))

    # Convert to ip_network object
    network = ipaddress.ip_network(f"{network_str}/{cidr}", strict=False)
    subnet_mask = str(network.netmask)
    loopback_ip = str(list(network.hosts())[0])  # First usable IP

    output.append([counter,loopback_ip,subnet_mask,network.network_address])
    counter += 1

for counter, loopback_ip, subnet_mask, network_address in output:
    print(f"""interface vlan{counter}
  ip address {loopback_ip} {subnet_mask}
vlan {counter}
 name test{counter}
 state active""")

for counter, loopback_ip, subnet_mask, network_address in output:
    print(f"""interface vlan{counter}
  shut
  no shut""")


print('router ospf 1')
for counter, loopback_ip, subnet_mask, network_address in output:
    print(f" network {network_address} {subnet_mask} area 0")

