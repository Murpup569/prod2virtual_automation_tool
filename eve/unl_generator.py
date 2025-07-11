import json
import os
import uuid
import xml.etree.ElementTree as ET

EVE_TEST_MODE = False

DEFAULT_ROUTER = {
    "template": "csr1000vng",
    "eve_image": "csr1000vng-universalk9.17.03.02.Amsterdam",
    "icon": "Router.png"
}
DEFAULT_SWITCH = {
    "template": "viosl2",
    "eve_image": "viosl2-adventerprisek9-m.SSA.high_iron_20180619",
    "icon": "Switch.png"
}

def generate_unl_file(topology, output_path, model_info, model_map_file, interface_maps):
    def get_iface_index(host, iface):
        if iface in iface_indexes[host]:
            return iface_indexes[host][iface]
        new_index = len(iface_indexes[host])
        iface_indexes[host][iface] = new_index
        return new_index

    with open(model_map_file) as f:
        model_map_raw = json.load(f)

    model_map = {}
    for model, data in model_map_raw.items():
        model_map[model] = {
            "eve_image": data.get("eve_image", "viosl2-adventerprisek9-m.SSA.high_iron_20180619"),
            "template": data.get("template", "viosl2"),
            "ram": data.get("ram", 2048),
            "icon": data.get("icon", "Router.png")  # use default icon fallback
        }

    # Dynamically count required ethernet interfaces
    interface_counts = {}
    for local_host, links in topology.items():
        interface_counts[local_host] = len(set(links.keys())) + 1  # Add 1 as buffer

    node_ids = {}
    iface_indexes = {}
    root = ET.Element("lab", name="AutoLab", version="1", scripttimeout="300", lock="0")
    topology_elem = ET.SubElement(root, "topology")
    nodes_elem = ET.SubElement(topology_elem, "nodes")
    node_id = 1

    connection_map = {}
    net_id_counter = 1

    for h1 in topology:
        for iface1, h2 in topology[h1].items():
            h2 = h2.split('.')[0]
            iface2 = find_interface_pointing_back(topology, h2, h1)
            if iface2 is None:
                continue
            key = tuple(sorted([(h1, iface1), (h2, iface2)]))
            if key not in connection_map:
                connection_map[key] = net_id_counter
                net_id_counter += 1

    net_id = net_id_counter

    for hostname in topology:
        model = model_info.get(hostname, "unknown")
        iface_indexes[hostname] = {}

        if EVE_TEST_MODE:
            is_switch = hostname.lower().startswith("sw")
            fallback = DEFAULT_SWITCH if is_switch else DEFAULT_ROUTER
            mapped = {
                "eve_image": fallback["eve_image"],
                "template": fallback["template"],
                "ram": 2048,
                "icon": fallback["icon"]
            }
        else:
            if model in model_map:
                mapped = model_map[model]
            else:
                mapped = {
                    "eve_image": "viosl2-adventerprisek9-m.SSA.high_iron_20180619",
                    "template": "viosl2",
                    "ram": 2048,
                    "icon": "Router.png"
                }

        node_uuid = str(uuid.uuid4())
        eth_count = interface_counts.get(hostname, 1)

        node_elem = ET.SubElement(nodes_elem, "node", {
            "id": str(node_id),
            "name": hostname,
            "type": "qemu",
            "template": mapped["template"],
            "image": mapped["eve_image"],
            "console": "telnet",
            "cpu": "1",
            "cpulimit": "0",
            "ram": str(mapped["ram"]),
            "ethernet": str(eth_count),
            "uuid": node_uuid,
            "left": str(200 * node_id),
            "top": "200",
            "icon": mapped["icon"],
            "config": "0"
        })

        if hostname in topology and hostname in interface_maps:
            for local_iface, neighbor in topology[hostname].items():
                mapped_name = interface_maps[hostname].get(local_iface, local_iface)
                iface_index = get_iface_index(hostname, mapped_name)
                remote_host = neighbor.split(".")[0]
                remote_iface = find_interface_pointing_back(topology, remote_host, hostname)
                if remote_iface is None:
                    print(f"[WARN] Could not find reverse interface from {remote_host} to {hostname}")
                    continue
                key = tuple(sorted([(hostname, local_iface), (remote_host, remote_iface)]))
                if key not in connection_map:
                    continue
                ET.SubElement(node_elem, "interface", {
                    "id": str(iface_index),
                    "name": mapped_name,
                    "type": "ethernet",
                    "network_id": str(connection_map[key])
                })

        node_ids[hostname] = node_id
        node_id += 1

    networks_elem = ET.SubElement(topology_elem, "networks")
    for i in range(1, net_id):
        ET.SubElement(networks_elem, "network", {
            "id": str(i),
            "type": "bridge",
            "name": f"Net-Switchiface_{i - 1}",
            "left": "462",
            "top": "175",
            "visibility": "0"
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    tree = ET.ElementTree(root)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    return node_ids

def find_interface_pointing_back(topology, remote_host, local_host):
    for iface, neighbor in topology.get(remote_host, {}).items():
        if neighbor.startswith(local_host):
            return iface
    interfaces = list(topology.get(remote_host, {}).keys())
    return interfaces[0] if interfaces else None
