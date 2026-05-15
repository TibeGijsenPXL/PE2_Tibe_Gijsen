# 🌐 Network as Code – PE2 Evaluatie
**End-to-End Automatisering van Cisco IOS-XE via YANG, NETCONF en RESTCONF**

> LAB 8.2 – Projectopdracht Network as Code  
> Student: Tibe Gijsen | PXL University of Applied Sciences

---

## 📋 Overzicht

Dit repository is de **single source of truth** voor de end-to-end automatisering van een fysieke Cisco IOS-XE router via YANG-modellering, NETCONF en RESTCONF.

De pipeline haalt configuratiebestanden op uit GitHub en deployt deze automatisch op het netwerkapparaat zonder enige manuele CLI-interventie.

---

## 🏗️ Architectuur

```
┌─────────────────────────────────────────────────────┐
│           GitHub – Single Source of Truth            │
│         TibeGijsenPXL/PE2_Tibe_Gijsen               │
│                                                      │
│   netconf_config.xml    restconf_config.json         │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP GET
                       ▼
┌─────────────────────────────────────────────────────┐
│              Ubuntu – Automatiseringsplatform        │
│                                                      │
│   end_to_end_pipeline.py (Python)                    │
│   ansible_playbook.yml   (Ansible)                   │
└──────────┬──────────────────────────┬───────────────┘
           │ NETCONF (poort 830)      │ RESTCONF (HTTPS)
           ▼                          ▼
┌─────────────────────────────────────────────────────┐
│         Cisco IOS-XE – LAB-RA05-C01-R01             │
│         IP: 10.199.65.109/27                         │
└─────────────────────────────────────────────────────┘
```

---

## 📁 Repository structuur

```
PE2_Tibe_Gijsen/
│
├── README.md                    # Dit bestand
├── netconf_config.xml           # YANG-XML configuratie (NETCONF)
├── restconf_config.json         # YANG-JSON configuratie (RESTCONF)
├── end_to_end_pipeline.py       # Python end-to-end pipeline
├── ansible_playbook.yml         # Ansible playbook
└── basis_config.txt             # Router én switch basisconfiguratie
```

---

## ⚙️ Vereisten

### Software
| Tool | Versie |
|------|--------|
| Python | 3.12 |
| paramiko | 2.12.0 |
| ncclient | latest |
| requests | latest |
| ansible | latest |
| ansible.netcommon | latest |

### Installatie
```bash
pip install ncclient paramiko==2.12.0 requests ansible
ansible-galaxy collection install ansible.netcommon
```

### Router vereisten
```
netconf-yang
restconf
ip http server
ip http secure-server
```

---

## 🚀 Gebruik

### Python pipeline
```bash
python end_to_end_pipeline.py
```

### Ansible playbook
```bash
ansible-playbook ansible_playbook.yml
```

---

## 🔄 Pipeline stappen

### Python (`end_to_end_pipeline.py`)

| Stap | Actie | Protocol |
|------|-------|----------|
| 1 | Configuratie ophalen uit GitHub | HTTP GET |
| 2 | Verbinding maken met router | NETCONF |
| 3 | Configuratie deployen | NETCONF edit-config |
| 4 | Verificatie | RESTCONF GET |
| 5 | Rapport genereren | - |

### Ansible (`ansible_playbook.yml`)

| Stap | Actie | Module |
|------|-------|--------|
| 1 | Configuratie ophalen uit GitHub | get_url |
| 2 | Deployen via RESTCONF | uri (PUT) |
| 3 | Verificatie via NETCONF | netconf_get |
| 4 | Rapport tonen | debug |

---

## 📡 YANG Modellen

| Model | Namespace | Gebruik |
|-------|-----------|---------|
| Cisco-IOS-XE-native | `http://cisco.com/ns/yang/Cisco-IOS-XE-native` | Hostname, interfaces, routing |
| Cisco-IOS-XE-ospf | `http://cisco.com/ns/yang/Cisco-IOS-XE-ospf` | OSPF configuratie |
| Cisco-IOS-XE-acl | `http://cisco.com/ns/yang/Cisco-IOS-XE-acl` | ACL configuratie |
| Cisco-IOS-XE-snmp | `http://cisco.com/ns/yang/Cisco-IOS-XE-snmp` | SNMP configuratie |
| ietf-interfaces | `urn:ietf:params:xml:ns:yang:ietf-interfaces` | Interface operationele data |

---

## 🌐 RESTCONF URLs

| Operatie | Methode | URL |
|----------|---------|-----|
| Hostname | GET/PUT | `/restconf/data/Cisco-IOS-XE-native:native/hostname` |
| Loopback0 | GET/PUT | `/restconf/data/Cisco-IOS-XE-native:native/interface/Loopback=0` |
| OSPF | GET/PUT | `/restconf/data/Cisco-IOS-XE-native:native/router/Cisco-IOS-XE-ospf:ospf=1` |
| ACL | GET | `/restconf/data/Cisco-IOS-XE-native:native/ip/access-list` |

---

## 🖥️ Laboratoriumopstelling

| Apparaat | Hostname | IP | Rol |
|----------|----------|----|-----|
| Router | LAB-RA05-C01-R01 | 10.199.65.109/27 | Cisco IOS-XE router |
| Switch | LAB-RA05-C01-SW01 | 172.17.5.2/28 | Cisco IOS switch |
| Ubuntu | tibe-yang | DHCP | Automatiseringsplatform |

### VLANs
| VLAN | Naam | Subnet |
|------|------|--------|
| 51 | Management | 172.17.5.0/28 |
| 52 | Data_Users | 172.17.5.16/28 |
| 53 | Voice_Users | 172.17.5.32/28 |
| 54 | Reserved | 172.17.5.48/28 |
| 99 | Native | - |

---

## 🔒 SSH Fix

De fysieke Cisco router gebruikt oudere SSH algoritmen. Paramiko 2.12.0 is vereist:

```bash
pip install paramiko==2.12.0
```

```python
from paramiko.transport import Transport
Transport._preferred_kex = ("diffie-hellman-group14-sha1",)
Transport._preferred_keys = ("ssh-rsa",)
```

---

## ✅ Geconfigureerde onderdelen

| Onderdeel | Waarde | Status |
|-----------|--------|--------|
| Hostname | LAB-RA05-C01-R01 | ✅ |
| GigabitEthernet0/0/1 | WAN interface | ✅ |
| GigabitEthernet0/0/0 | LAN interface | ✅ |
| Loopback0 | 1.1.1.1/32 | ✅ |
| OSPF Process 1 | Router-ID 1.1.1.1 | ✅ |
| ACL NAC_ACL | permit 10.199.65.96/27 | ✅ |
| SNMP | community public RO | ✅ |
| Banner MOTD | Tibe Gijsen PXL | ✅ |

---

## 👨‍💻 Auteur

**Tibe Gijsen**  
PXL University of Applied Sciences  
Network Programmability – LAB 8.2 PE2  
GitHub: [TibeGijsenPXL](https://github.com/TibeGijsenPXL)
