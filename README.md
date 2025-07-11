# AutoLab Builder

AutoLab Builder automates the extraction of live network device configurations and topology, cleans and normalizes interface names, and generates an EVE-NG `.unl` topology file plus startup configs ready for import.
Note: I was not have to get the interfaces in the config matching the CDP information, but it's added to my TODO list!

## Prerequisites

- Python 3.7+
- `pip install -r requirements.txt`

## Installation

```bash
git clone https://github.com/Murpup569/prod2virtual_automation_tool.git
cd AutoLab-Builder
pip install -r requirements.txt

## Configuration

1. **Inventory**  
   Edit `inventory.csv` (columns: `hostname,ip,device_type`).

2. **Model Map**  
   Update `model_map.json` with your device-to-EVE image/RAM/NIC mappings.

## Usage

```bash
python main.py
```

This will:

1. SSH into each device (Netmiko) and pull `show run`, `show cdp neighbors detail`, etc.  
2. Parse outputs into structured topology (Genie parsers → JSON/YAML).  
3. (Optional) Visualize with NetworkX/Matplotlib.  
4. Normalize interface names and strip unsupported commands.  
5. Write cleaned configs to `output/configs/`.  
6. Generate `output/AutoLab.unl`.

## Importing into EVE-NG

1. **Copy the `.unl` file** to your EVE-NG server:
   ```bash
   scp output/AutoLab.unl root@<EVE_IP>:/opt/unetlab/labs/<LabName>/
   ```
2. **Copy startup configs** into each node’s tmp folder (match node IDs in the lab):
   ```bash
   scp output/configs/<hostname>_startup.cfg root@<EVE_IP>:/opt/unetlab/tmp/0/node-<node_id>/startup-config.cfg
   ```
3. In the EVE-NG Web UI, go to **Import** → select your `.unl` file.  
4. Open the lab, **Start** nodes, and your configs will be applied automatically.

*Happy labbing!*  
