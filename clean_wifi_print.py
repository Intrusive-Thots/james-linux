import re

with open("james/gui/main_window.py", "r") as f:
    lines = f.readlines()

out_lines = []
in_wifi_print = False
for line in lines:
    if line.strip().startswith("self._wifi_print("):
        continue
    if line.startswith("    def _wifi_print("):
        in_wifi_print = True
        continue
    
    if in_wifi_print:
        if line.strip() == "" or line.startswith("        ") or line.startswith("\t"):
            continue
        else:
            in_wifi_print = False
    
    out_lines.append(line)

with open("james/gui/main_window.py", "w") as f:
    f.writelines(out_lines)
