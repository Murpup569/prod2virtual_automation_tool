from ciscoconfparse import CiscoConfParse
import re

def remove_unsupported_commands(config):
    parse = CiscoConfParse(config.splitlines(), syntax="ios", ignore_blank_lines=False)

    parent_filters = [
        "^username ",
        "^aaa ",
        "^radius-server ",
        "^radius server ",
        "^platform ",
        "^enable secret",
        "^password ",
        "^line vty",
        "^line con",
        "^line aux",
        "^key ",
        "^crypto ",
        "^snmp-server ",
        "^call-home",
        "^ip http ",
        "^control-plane",
        "^ip forward-protocol ",
        "^redundancy",
        "^license ",
        "^diagnostic ",
        "^memory ",
        "^multilink ",
        "^login ",
        "^subscriber ",
        "^no aaa ",
        "^service ",
        "^version ",
        "^Building ",
        "^Current ",
        "^vrf definition Mgmt-vrf",
        r"^switch \d+ provision",
    ]

    for regex in parent_filters:
        objs = parse.find_objects(regex)
        for obj in objs:
            obj.delete()

    return "\n".join(parse.ioscfg)

def normalize_config_interfaces(config):
    lines = config.splitlines()
    interface_map = {}
    current_intf = None
    counter = 0
    updated_lines = []

    for line in lines:
        if line.strip().startswith("interface"):
            current_intf = line.strip().split("interface", 1)[1].strip()
            module = counter // 4
            port = counter % 4
            eve_name = f"Ethernet{module}/{port}"
            interface_map[current_intf] = eve_name
            updated_lines.append(f"interface {eve_name}")
            counter += 1
        else:
            if current_intf:
                for orig, new in interface_map.items():
                    line = re.sub(rf"\b{re.escape(orig)}\b", new, line)
            updated_lines.append(line)

    return "\n".join(updated_lines), interface_map