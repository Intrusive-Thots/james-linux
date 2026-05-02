from typing import Dict, Any
from .base_server import MCPToolClient
from james.layers.native import NativeLayer
import json
import xml.etree.ElementTree as ET

class NmapServer(MCPToolClient):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(NmapServer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, layer: NativeLayer = None):
        if not getattr(self, '_initialized', False):
            super().__init__("Nmap MCP Server")
            self.layer = layer if layer else NativeLayer()
            self._initialized = True

            self.register_tool(
                "nmap_scan",
                "Run an nmap scan on a target. Arguments: target (str), options (str, optional).",
                self.nmap_scan
            )

    def nmap_scan(self, target: str, options: str = "-T4 -F") -> Dict[str, Any]:
        cmd = f"nmap {options} -oX - {target}"
        result = self.layer.run(cmd, timeout=300)

        if result.returncode != 0:
            return {"status": "error", "message": result.stderr}

        try:
            root = ET.fromstring(result.stdout)
            hosts = []
            for host in root.findall('host'):
                address = host.find('address').get('addr')
                status = host.find('status').get('state')

                ports_list = []
                ports = host.find('ports')
                if ports:
                    for port in ports.findall('port'):
                        portid = port.get('portid')
                        state = port.find('state').get('state')
                        service = port.find('service')
                        name = service.get('name') if service is not None else 'unknown'
                        ports_list.append({"port": portid, "state": state, "service": name})

                hosts.append({"address": address, "status": status, "ports": ports_list})

            return {"status": "success", "hosts": hosts}
        except Exception as e:
            return {"status": "error", "message": f"Failed to parse nmap xml: {e}"}
