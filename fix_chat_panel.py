import re

with open("james/gui/chat_panel.py", "r") as f:
    content = f.read()

# Fix the shortcut text from Ctrl+1-7 to Ctrl+1-4
content = content.replace("Ctrl+1-7", "Ctrl+1-4")

# Remove the Right-click menus table row
old_row = """    <tr>
      <td style="padding: 4px 8px; color: #ff6b35;">🖱️ Right-click menus</td>
      <td style="padding: 4px 8px; color: #4a6a8a;">→ Recon &amp; AP tables: scan, copy, attack</td>
    </tr>"""
content = content.replace(old_row, "")

with open("james/gui/chat_panel.py", "w") as f:
    f.write(content)
