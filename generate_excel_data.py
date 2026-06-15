import pandas as pd
import random
from datetime import datetime, timedelta

ROWS = 1000

domains = ["FABNET", "CORPNET", "TESTNET"]

models = [
    "HP Z440 Workstation",
    "HP EliteDesk 800 G6",
    "Dell OptiPlex 7090",
    "Dell Precision 5820",
    "Lenovo ThinkCentre M720",
    "HP Z2 G5",
    "Lenovo ThinkStation P330",
    "Dell OptiPlex 7080"
]

agent_versions = [
    "5.7.7.378",
    "5.8.4.505",
    "5.8.4.610",
    "5.9.1.112"
]

users = [
    "Administrator",
    "admin",
    "operator",
    "testuser",
    "svcuser",
    "N/A"
]

rows = []

base_time = datetime(2026, 1, 27, 8, 0, 0)

# DHCP binding records that should match
binding_records = {}

for i in range(35, 135):
    mac = f"a464a913ed{(i-35+43):02x}"
    binding_records[f"10.143.12.{i}"] = mac.upper()

for i in range(1, ROWS + 1):

    if i <= 100:
        ip = f"10.143.12.{34+i}"
        mac = binding_records[ip]
    else:
        ip = f"10.{random.randint(100,150)}.{random.randint(1,254)}.{random.randint(1,254)}"

        mac = "".join(
            random.choice("0123456789ABCDEF")
            for _ in range(12)
        )

    # Intentional duplicate IPs
    if i % 100 == 0:
        ip = "10.143.12.50"

    # Intentional IP/MAC mismatch
    if i % 75 == 0:
        mac = "FFFFFFFFFFFF"

    timestamp = (
        base_time +
        timedelta(
            days=random.randint(0,120),
            hours=random.randint(0,23),
            minutes=random.randint(0,59),
            seconds=random.randint(0,59)
        )
    )

    rows.append({
        "SR NO.": i,
        "IP address": ip,
        "Computer Name": f"PC-{random.randint(1000,9999)}",
        "Domain Name": random.choice(domains),
        "ESTP Ver": "10.7.0.3497",
        "ESTP DAT Ver": random.choice(["6145","6201","6255"]),
        "Agent Ver": random.choice(agent_versions),
        "ESATP Ver": "10.7.0.3590",
        "DLPE Ver": "11.9.0.822",
        "Last Agent Comm": timestamp.strftime("%d/%m/%y %H:%M:%S IST"),
        "User Name": random.choice(users),
        "MAC Address": mac,
        "System Model": random.choice(models)
    })

df = pd.DataFrame(rows)

df.to_excel(
    "endpoint_inventory_1000.xlsx",
    index=False
)

print("Created endpoint_inventory_1000.xlsx")