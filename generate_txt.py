import pandas as pd

excel_file = "endpoint_inventory_1000.xlsx"
out_path = "ip_source_binding_generated.txt"

df = pd.read_excel(excel_file)

ip_col = next((c for c in df.columns if "ip" in str(c).lower()), None)
mac_col = next((c for c in df.columns if "mac" in str(c).lower()), None)

print("IP Column:", ip_col)
print("MAC Column:", mac_col)

lines = []

for _, row in df.iterrows():
    ip = str(row[ip_col]).strip()
    mac = str(row[mac_col]).strip()

    if ip.lower() == "nan" or mac.lower() == "nan":
        continue

    mac = mac.replace(":", "").replace("-", "").replace(".", "").replace(" ", "")

    if len(mac) == 12:
        mac = f"{mac[:4]}-{mac[4:8]}-{mac[8:12]}".lower()

    lines.append(
        f"ip source binding ip-address {ip} mac-address {mac} vlan 4"
    )

with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Generated {len(lines)} entries")
print(f"Output file: {out_path}")