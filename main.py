import csv
import os
import re
from netmiko import ConnectHandler
from ttp import ttp
from config.cleaner import normalize_config_interfaces, remove_unsupported_commands
from eve.unl_generator import generate_unl_file
import json
import networkx as nx
import matplotlib.pyplot as plt
import getpass

INVENTORY_FILE = "inventory.csv"
CONFIG_DIR = "output/configs"
UNL_PATH = "output/AutoLab.unl"
MODEL_MAP_FILE = "model_map.json"
TTP_TEMPLATE_PATH = "parser/templates"
SSH_USERNAME = input("Username:")
SSH_PASSWORD = getpass.getpass("Password:")

def load_inventory_from_csv(path):
    with open(path, newline='') as csvfile:
        return list(csv.DictReader(csvfile))

def ensure_output_dirs():
    os.makedirs(CONFIG_DIR, exist_ok=True)

def run_commands(device):
    commands = ["show running-config", "show cdp neighbors detail", "show version", "show inventory"]
    connection = ConnectHandler(
        ip=device["ip"],
        device_type=device["device_type"],
        username=SSH_USERNAME,
        password=SSH_PASSWORD,
    )
    output = {}
    for cmd in commands:
        output[cmd] = connection.send_command(cmd)
    connection.disconnect()
    return output

def extract_model_id(parsed_inventory, show_version):
    try:
        # Try inventory first
        if parsed_inventory:
            entries = parsed_inventory[0]
            if isinstance(entries, list):
                entries = entries[0]
            for item in entries:
                if "model_id" in item:
                    return item["model_id"]
    except (IndexError, TypeError, AttributeError):
        pass

    # Fallback: try to regex model from show version string
    try:
        raw_text = show_version
        if isinstance(raw_text, str):
            match = re.search(r"Model Number                       : (\S+)", raw_text)
            if match:
                return match.group(1)
        elif isinstance(raw_text, list):
            for line in raw_text:
                if isinstance(line, str):
                    match = re.search(r"Model Number                       : (\S+)", line)
                    if match:
                        return match.group(1)
    except Exception:
        pass

    return "unknown"

def parse_output_with_ttp(template_file, data):
    with open(template_file, "r") as f:
        template = f.read()
    parser = ttp(data=data, template=template)
    parser.parse()
    return parser.result(format="json")

def visualize_topology(topology):
    G = nx.Graph()
    for node, neighbors in topology.items():
        for intf, neighbor in neighbors.items():
            G.add_edge(node, neighbor)
    nx.draw(G, with_labels=True)
    plt.show()

def build_cleaned_outputs(inventory):
    raw_configs = {}
    cdp_data = {}
    version_data = {}
    interface_maps = {}

    for device in inventory:
        print(f"[*] Connecting to {device['hostname']}...")
        output = run_commands(device)
        cleaned, iface_map = normalize_config_interfaces(remove_unsupported_commands(output["show running-config"]))
        raw_configs[device["hostname"]] = cleaned
        interface_maps[device["hostname"]] = iface_map

        parsed_cdp = parse_output_with_ttp(f"{TTP_TEMPLATE_PATH}/cdp_neighbors.ttp", output["show cdp neighbors detail"])
        parsed_inventory = parse_output_with_ttp(f"{TTP_TEMPLATE_PATH}/show_inventory.ttp", output["show inventory"])

        cdp_entries = json.loads(parsed_cdp[0])
        if isinstance(cdp_entries, list) and len(cdp_entries) == 1 and isinstance(cdp_entries[0], list):
            cdp_entries = cdp_entries[0]

        filtered_entries = []
        for entry in cdp_entries:
            if "local_interface" not in entry:
                continue  # Skip phones or malformed entries
            original = entry["local_interface"]
            entry["local_interface"] = iface_map.get(original, original)
            # Strip domain suffix from remote_host
            if "remote_host" in entry:
                entry["remote_host"] = entry["remote_host"].split('.')[0]
            filtered_entries.append(entry)

        cdp_data[device["hostname"]] = filtered_entries
        version_data[device["hostname"]] = extract_model_id(parsed_inventory, output["show version"])

    return raw_configs, cdp_data, version_data, interface_maps

def build_topology_from_cdp(cdp_data):
    topology = {}
    for hostname, entries in cdp_data.items():
        topology[hostname] = {}
        for entry in entries:
            topology[hostname][entry["local_interface"]] = entry["remote_host"]
    return topology

if __name__ == "__main__":
    ensure_output_dirs()

    print("[*] Loading inventory...")
    inventory = load_inventory_from_csv(INVENTORY_FILE)

    print("[*] Cleaning and collecting data...")
    raw_configs, cdp_data, model_info, interface_maps = build_cleaned_outputs(inventory)

    print("[*] Building topology from cleaned data...")
    topology_data = build_topology_from_cdp(cdp_data)

    print("[*] Visualizing topology...")
    visualize_topology(topology_data)

    print(f"[*] Writing startup configs to {CONFIG_DIR} folder...")
    os.makedirs(CONFIG_DIR, exist_ok=True)
    for hostname, cfg in raw_configs.items():
        with open(f"{CONFIG_DIR}/{hostname}.cfg", "w") as f:
            f.write(cfg)

    print("[*] Generating EVE-NG .unl file...")
    node_ids = generate_unl_file(topology_data, UNL_PATH, model_info, MODEL_MAP_FILE, interface_maps)

    print("[*] Writing startup configs to .unl.cfg folder...")
    lab_cfg_dir = UNL_PATH + ".cfg"
    os.makedirs(lab_cfg_dir, exist_ok=True)
    for hostname, cfg in raw_configs.items():
        if hostname in node_ids:
            node_id = node_ids[hostname]
            with open(f"{lab_cfg_dir}/{node_id}.cfg", "w") as f:
                f.write(cfg)

    print("[+] AutoLab build complete! Load the .unl file in EVE-NG.")
