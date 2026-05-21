import re

with open("james/gui/main_window.py", "r") as f:
    lines = f.readlines()

funcs_to_remove = [
    "_make_agent_tab",
    "_make_quick_actions_panel",
    "_qa_send",
    "_make_context_strip",
    "_refresh_context_strip",
    "_make_recon_tab",
    "_recon_context_menu",
    "_do_recon_cmd",
    "_make_wifi_tab",
    "_make_cracking_tab",
    "_populate_captures",
    "_populate_wordlist_combo",
    "_browse_combo",
    "_get_wordlist_path",
    "_run_agent_cmd",
    "_set_target_from_menu",
    "_ap_context_menu",
    "_do_quick_scan",
    "_do_full_scan",
    "_populate_recon",
    "_refresh_interfaces",
    "_update_iface_combo",
    "_toggle_monitor",
    "_do_deauth",
    "_do_crack_wpa",
    "_do_autopwn",
    "_do_crack_hash",
    "_show_crack_result",
    "_browse",
    "_do_ap_scan",
    "_populate_ap_table",
    "_ap_table_select",
    "_refresh_loot",
    "_do_wifi_blitz",
    "_do_network_dominate",
    "_do_web_pwn",
    "_do_stealth_recon",
]

out_lines = []
in_target_func = False

for line in lines:
    if line.startswith("    def "):
        func_name = line.split("def ")[1].split("(")[0]
        if func_name in funcs_to_remove:
            in_target_func = True
            continue
        else:
            in_target_func = False

    if in_target_func:
        # If it's empty line or indented more than 4 spaces, skip
        if (
            line.strip() == ""
            or line.startswith("        ")
            or line.startswith("    #")
            or line.startswith("\t")
        ):
            continue
        else:
            # We are out of the function block
            in_target_func = False

    out_lines.append(line)

with open("james/gui/main_window.py", "w") as f:
    f.writelines(out_lines)
