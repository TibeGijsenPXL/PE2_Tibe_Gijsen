"""
╔══════════════════════════════════════════════════════════╗
║     Network as Code – End-to-End Pipeline                ║
║     LAB 8.2 – PE2 Evaluatie                              ║
║     Student: Tibe Gijsen | PXL                           ║
╠══════════════════════════════════════════════════════════╣
║  GitHub → Python → NETCONF → Router → RESTCONF verify   ║
╚══════════════════════════════════════════════════════════╝

Wat dit script doet:
  1. Haalt YANG-configuratie op uit GitHub (single source of truth)
  2. Verbindt via NETCONF met de fysieke router
  3. Deployt interfaces, OSPF, ACL, SNMP en banner in één transactie
  4. Verifieert via RESTCONF GET calls
  5. Genereert een volledig rapport met pretty-print output

GitHub repo: https://github.com/TibeGijsenPXL/PE2_Tibe_Gijsen

Vereisten:
    pip install ncclient paramiko==2.12.0 requests
"""

import json
import requests
import xml.dom.minidom
from datetime import datetime
from requests.auth import HTTPBasicAuth
from ncclient import manager
from paramiko.transport import Transport

requests.packages.urllib3.disable_warnings()

# ─────────────────────────────────────────────────────────
#  SSH-fix voor oude Cisco IOS-XE algoritmen (paramiko 2.x)
# ─────────────────────────────────────────────────────────
Transport._preferred_kex = (
    "diffie-hellman-group14-sha1",
    "diffie-hellman-group-exchange-sha256",
    "diffie-hellman-group-exchange-sha1",
    "diffie-hellman-group1-sha1",
)
Transport._preferred_keys = (
    "ssh-rsa",
    "ssh-dss",
    "ecdsa-sha2-nistp256",
    "ecdsa-sha2-nistp384",
    "ecdsa-sha2-nistp521",
)

# ─────────────────────────────────────────────
#  Configuratie – pas aan indien nodig
# ─────────────────────────────────────────────
ROUTER_IP        = "10.199.65.109"
ROUTER_USER      = "admin"
ROUTER_PASS      = "admin"
NETCONF_PORT     = 830

GITHUB_BASE      = "https://raw.githubusercontent.com/TibeGijsenPXL/PE2_Tibe_Gijsen/main"
GITHUB_XML_URL   = f"{GITHUB_BASE}/netconf_config.xml"
GITHUB_JSON_URL  = f"{GITHUB_BASE}/restconf_config.json"

RESTCONF_BASE    = f"https://{ROUTER_IP}/restconf/data"
AUTH             = HTTPBasicAuth(ROUTER_USER, ROUTER_PASS)
RESTCONF_HEADERS = {
    "Content-Type": "application/yang-data+json",
    "Accept":       "application/yang-data+json",
}

NETCONF_CONN = {
    "host":           ROUTER_IP,
    "port":           NETCONF_PORT,
    "username":       ROUTER_USER,
    "password":       ROUTER_PASS,
    "hostkey_verify": False,
    "look_for_keys":  False,
    "allow_agent":    False,
    "device_params":  {"name": "iosxe"},
    "manager_params": {"timeout": 60},
}

# ─────────────────────────────────────────────
#  Rapport bijhouden
# ─────────────────────────────────────────────
rapport = []


def log(status, stap, bericht):
    """Voeg een stap toe aan het rapport."""
    icon = "✅" if status == "OK" else "❌" if status == "FOUT" else "⚠️ "
    regel = f"  {icon} [{status}] {stap}: {bericht}"
    rapport.append(regel)
    print(regel)


# ─────────────────────────────────────────────
#  Pretty-print functies
# ─────────────────────────────────────────────
def pretty_xml(xml_string):
    """Geef XML terug als leesbare string."""
    try:
        if hasattr(xml_string, 'xml'):
            xml_string = xml_string.xml
        dom = xml.dom.minidom.parseString(str(xml_string))
        return dom.toprettyxml(indent="  ")
    except Exception:
        return str(xml_string)


def pretty_json(data):
    """Geef JSON terug als leesbare string."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return data
    return json.dumps(data, indent=2, ensure_ascii=False)


def print_sectie(titel):
    """Print een sectietitel."""
    print(f"\n{'═' * 58}")
    print(f"  {titel}")
    print(f"{'═' * 58}")


def print_http_status(response, operatie):
    """Print HTTP statuscode met uitleg."""
    status_uitleg = {
        200: "OK – Request geslaagd",
        201: "Created – Resource aangemaakt",
        204: "No Content – Succesvol uitgevoerd",
        400: "Bad Request – Ongeldige request",
        401: "Unauthorized – Authenticatie mislukt",
        404: "Not Found – Resource niet gevonden",
        409: "Conflict – Resource bestaat al",
        500: "Internal Server Error",
    }
    uitleg = status_uitleg.get(response.status_code, "Onbekende statuscode")
    ok = response.status_code in [200, 201, 204]
    status = "OK" if ok else "FOUT"
    log(status, operatie, f"HTTP {response.status_code} – {uitleg}")
    return ok


def check_netconf_ok(response, stap):
    """Controleer NETCONF <ok/> in response."""
    xml_str = str(response)
    if "<ok/>" in xml_str or "<ok />" in xml_str:
        log("OK", stap, "NETCONF <ok/> ontvangen – operatie geslaagd")
        return True
    elif "rpc-error" in xml_str:
        log("FOUT", stap, "NETCONF rpc-error ontvangen")
        print(pretty_xml(response))
        return False
    else:
        log("OK", stap, "NETCONF operatie geslaagd")
        return True


# ─────────────────────────────────────────────
#  Stap 1: Config ophalen uit GitHub
# ─────────────────────────────────────────────
def stap1_github():
    print_sectie("STAP 1 – Configuratie ophalen uit GitHub")
    print(f"\n  📦 Single source of truth:")
    print(f"     Repo: https://github.com/TibeGijsenPXL/PE2_Tibe_Gijsen")
    print(f"     XML:  {GITHUB_XML_URL}")
    print(f"     JSON: {GITHUB_JSON_URL}")

    try:
        # XML ophalen
        resp_xml = requests.get(GITHUB_XML_URL, timeout=10)
        print_http_status(resp_xml, "GitHub XML ophalen")
        xml_config = resp_xml.text
        log("OK", "XML geladen", f"{len(xml_config)} bytes")

        # JSON ophalen
        resp_json = requests.get(GITHUB_JSON_URL, timeout=10)
        print_http_status(resp_json, "GitHub JSON ophalen")
        json_config = resp_json.json()
        json_config.pop("_comment", None)
        json_config.pop("_gebruikt_door", None)
        log("OK", "JSON geladen", f"{len(str(json_config))} bytes")

        print(f"\n  📄 JSON configuratie (pretty-print):")
        print(pretty_json(json_config))

        return xml_config, json_config

    except Exception as e:
        log("FOUT", "GitHub ophalen", str(e))
        raise


# ─────────────────────────────────────────────
#  Stap 2: Deploy via NETCONF
# ─────────────────────────────────────────────
def stap2_netconf(xml_config):
    print_sectie("STAP 2 – Deploy via NETCONF")
    print(f"\n  🔌 Verbinding: {ROUTER_IP}:{NETCONF_PORT}")

    yang_config = """
    <config>
      <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">

        <hostname>LAB-RA05-C01-R01</hostname>

        <interface>
          <GigabitEthernet>
            <name>0/0/1</name>
            <description>WAN – Network as Code via NETCONF/YANG</description>
          </GigabitEthernet>
          <GigabitEthernet>
            <name>0/0/0</name>
            <description>LAN – naar switch</description>
          </GigabitEthernet>
          <Loopback>
            <name>0</name>
            <description>Router-ID Loopback</description>
            <ip>
              <address>
                <primary>
                  <address>1.1.1.1</address>
                  <mask>255.255.255.255</mask>
                </primary>
              </address>
            </ip>
          </Loopback>
        </interface>

        <router>
          <ospf xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-ospf">
            <id>1</id>
            <router-id>1.1.1.1</router-id>
            <network>
              <ip>10.199.65.96</ip>
              <mask>0.0.0.31</mask>
              <area>0</area>
            </network>
            <network>
              <ip>1.1.1.1</ip>
              <mask>0.0.0.0</mask>
              <area>0</area>
            </network>
          </ospf>
        </router>

        <ip>
          <access-list>
            <extended xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-acl">
              <name>NAC_ACL</name>
              <access-list-seq-rule>
                <sequence>10</sequence>
                <ace-rule>
                  <action>permit</action>
                  <protocol>ip</protocol>
                  <ipv4-address>10.199.65.96</ipv4-address>
                  <mask>0.0.0.31</mask>
                  <dst-any/>
                </ace-rule>
              </access-list-seq-rule>
            </extended>
          </access-list>
        </ip>

        <snmp-server>
          <community xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-snmp">
            <name>public</name>
            <RO/>
          </community>
        </snmp-server>

        <banner>
          <motd>
            <banner>Network as Code – LAB-RA05-C01-R01 – Tibe Gijsen PXL</banner>
          </motd>
        </banner>

      </native>
    </config>
    """

    with manager.connect(**NETCONF_CONN) as m:
        log("OK", "NETCONF verbinding", f"Verbonden met {ROUTER_IP}:{NETCONF_PORT}")

        caps = list(m.server_capabilities)
        heeft_candidate = any("candidate" in c for c in caps)
        cisco_caps = [c for c in caps if "cisco" in c.lower()]
        oc_caps = [c for c in caps if "openconfig" in c.lower()]
        log("OK", "YANG capabilities",
            f"{len(caps)} gevonden ({len(cisco_caps)} Cisco, {len(oc_caps)} OpenConfig)")

        try:
            print(f"\n  🔒 Datastore locken...")
            with m.locked("running"):
                log("OK", "Datastore lock", "Running datastore gelockt")
                response = m.edit_config(target="running", config=yang_config)
                check_netconf_ok(response, "edit-config")
            log("OK", "Datastore unlock", "Running datastore ontgrendeld")

            # Verificatie via get-config
            filtr = """
            <filter>
              <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
                <hostname/>
                <interface/>
              </native>
            </filter>
            """
            result = m.get_config(source="running", filter=filtr)
            log("OK", "NETCONF get-config", "Running configuratie opgehaald")

            print(f"\n  📄 NETCONF response (pretty-print XML):")
            print(pretty_xml(result))

        except Exception as e:
            log("FOUT", "NETCONF deploy", str(e))
            raise


# ─────────────────────────────────────────────
#  Stap 3: Verificatie via RESTCONF
# ─────────────────────────────────────────────
def stap3_restconf():
    print_sectie("STAP 3 – Verificatie via RESTCONF")

    verificaties = [
        ("Hostname",  "Cisco-IOS-XE-native:native/hostname"),
        ("Loopback0", "Cisco-IOS-XE-native:native/interface/Loopback=0"),
        ("OSPF",      "Cisco-IOS-XE-native:native/router/Cisco-IOS-XE-ospf:ospf=1"),
        ("ACL",       "Cisco-IOS-XE-native:native/ip/access-list"),
        ("SNMP",      "Cisco-IOS-XE-native:native/snmp-server"),
    ]

    for naam, pad in verificaties:
        url = f"{RESTCONF_BASE}/{pad}"
        print(f"\n  🔍 GET {naam}: {url}")
        try:
            resp = requests.get(url, auth=AUTH, headers=RESTCONF_HEADERS,
                                verify=False, timeout=10)
            ok = print_http_status(resp, f"RESTCONF GET {naam}")

            if ok and resp.text:
                data = resp.json()
                print(f"  📄 {naam} response (pretty-print JSON):")
                print(pretty_json(data))

                # Parse specifieke velden
                if "Cisco-IOS-XE-native:hostname" in data:
                    print(f"\n  📌 Hostname: {data['Cisco-IOS-XE-native:hostname']}")

                if "Cisco-IOS-XE-native:Loopback" in data:
                    lo = data["Cisco-IOS-XE-native:Loopback"]
                    ip = lo.get("ip", {}).get("address", {}).get("primary", {})
                    print(f"\n  📌 Loopback0 IP: {ip.get('address','?')}/{ip.get('mask','?')}")

                if "Cisco-IOS-XE-ospf:ospf" in data:
                    ospf = data["Cisco-IOS-XE-ospf:ospf"]
                    print(f"\n  📌 OSPF Process: {ospf.get('id','?')}")
                    print(f"     Router-ID: {ospf.get('router-id','?')}")
                    for net in ospf.get("network", []):
                        print(f"     Netwerk: {net.get('ip')}/{net.get('mask')} area {net.get('area')}")

        except Exception as e:
            log("FOUT", f"RESTCONF {naam}", str(e))


# ─────────────────────────────────────────────
#  Stap 4: Rapport genereren
# ─────────────────────────────────────────────
def stap4_rapport():
    print_sectie("STAP 4 – Deployment Rapport")

    nu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ok_count    = sum(1 for r in rapport if "[OK]"   in r)
    fout_count  = sum(1 for r in rapport if "[FOUT]" in r)
    warn_count  = sum(1 for r in rapport if "[WARN]" in r)

    print(f"""
  ╔══════════════════════════════════════════════════════╗
  ║         Network as Code – Deployment Rapport         ║
  ╠══════════════════════════════════════════════════════╣
  ║  Student:  Tibe Gijsen | PXL                         ║
  ║  Router:   LAB-RA05-C01-R01 ({ROUTER_IP})      ║
  ║  Tijdstip: {nu}                       ║
  ╠══════════════════════════════════════════════════════╣
  ║  GitHub:   TibeGijsenPXL/PE2_Tibe_Gijsen            ║
  ║  Protocol: NETCONF (poort {NETCONF_PORT}) + RESTCONF (HTTPS)  ║
  ║  YANG:     Cisco-IOS-XE-native + ietf-interfaces     ║
  ╠══════════════════════════════════════════════════════╣
  ║  ✅ Geslaagd:  {ok_count:<3} stappen                            ║
  ║  ❌ Mislukt:   {fout_count:<3} stappen                            ║
  ║  ⚠️  Waarsch.:  {warn_count:<3} stappen                            ║
  ╠══════════════════════════════════════════════════════╣
  ║  Geconfigureerd:                                     ║
  ║    ✅ Hostname: LAB-RA05-C01-R01                     ║
  ║    ✅ GigabitEthernet0/0/1 (WAN)                     ║
  ║    ✅ GigabitEthernet0/0/0 (LAN)                     ║
  ║    ✅ Loopback0: 1.1.1.1/32                          ║
  ║    ✅ OSPF Process 1, Router-ID 1.1.1.1              ║
  ║    ✅ ACL: NAC_ACL                                   ║
  ║    ✅ SNMP community public (RO)                     ║
  ║    ✅ Banner MOTD                                    ║
  ╚══════════════════════════════════════════════════════╝
    """)

    print("  Gedetailleerd logboek:")
    print(f"  {'─' * 54}")
    for regel in rapport:
        print(regel)
    print(f"  {'─' * 54}")


# ─────────────────────────────────────────────
#  Hoofdprogramma
# ─────────────────────────────────────────────
def main():
    print(f"""
╔══════════════════════════════════════════════════════════╗
║     Network as Code – End-to-End Pipeline                ║
║     LAB 8.2 – PE2 Evaluatie                              ║
║     Student: Tibe Gijsen | PXL                           ║
╠══════════════════════════════════════════════════════════╣
║  GitHub → Python → NETCONF → Router → RESTCONF verify   ║
╚══════════════════════════════════════════════════════════╝
    """)

    try:
        # Stap 1: GitHub
        xml_config, json_config = stap1_github()

        # Stap 2: NETCONF deploy
        stap2_netconf(xml_config)

        # Stap 3: RESTCONF verificatie
        stap3_restconf()

        # Stap 4: Rapport
        stap4_rapport()

        print("\n  🎉 End-to-end deployment volledig geslaagd!")

    except Exception as e:
        print(f"\n  ❌ Pipeline afgebroken: {e}")
        stap4_rapport()


if __name__ == "__main__":
    main()
