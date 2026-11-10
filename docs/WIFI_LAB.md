# Wi-Fi Part 1 Lab

JAMES runs the tutorial's radio and analysis steps as separate exercises. Use an isolated access point and client that you control. Change the access point's security, SSID broadcast, or MAC filter in its admin page to match each exercise. Reconnect the test client when prompted. [How to Hack WiFi (Part 1)](https://rumble.com/v7i16jw-how-to-hack-wifi-part-1.html)

## Desktop GUI

Open **Wi-Fi Lab** or press **Ctrl+5**. Choose an exercise and a dedicated adapter, then enter the lab BSSID and channel. **Use selected AP** copies those values from the access point you selected in Wi-Fi Arsenal. **Run exercise** starts the runner. **Stop** waits for the runner to restore the adapters.

**Findings** shows the observed AP and clients, exercise results, and saved paths. **Packets** uses TShark with a filter for the exercise and shows up to 200 matching rows from the first 10,000 captured frames. **Run log** shows progress and tool errors. The full capture is saved in the run directory. Install `tshark` for the packet table.

The desktop app uses your existing `sudo` authorization for the radio worker. If prompted to authorize it, run `sudo -v` in the terminal that launches JAMES, then start the GUI from that terminal. Elevated runs save their evidence under the root account unless you use the CLI with a different output directory.

## Start

On Parrot or Kali, install `iw`, `iproute2`, and `aircrack-ng`. Install `tshark` for hidden SSID, WPA3, twin, traffic, and WPA capture filtered to a client. The second-AP exercises use `hostapd`, and the traffic exercise also uses `tcpdump`. The capture adapter starts disconnected in managed mode and must support monitor mode. The twin and traffic exercises require a second physical radio with AP mode. The runner accepts 2.4 GHz channels 1–14. Set the channel to one supported by your hardware and regulatory domain.

```bash
python3 main.py wifi-lab --help

sudo .venv/bin/python main.py wifi-lab sniff \
  --interface wlan1 --bssid 02:11:22:33:44:55 --channel 6
```

Replace the example adapter, AP BSSID, and channel with your lab values. Use `iw dev` to list adapters. For subsequent commands, set your actual values once in the shell.

```bash
LAB_IFACE=wlan1
LAB_BSSID=02:11:22:33:44:55
LAB_CHANNEL=6
LAB_CLIENT=02:11:22:33:44:66
LAB_SECOND_IFACE=wlan2
LAB_WORDLIST="$PWD/lab-passwords.txt"

lab() {
  sudo .venv/bin/python main.py wifi-lab "$1" \
    --interface "$LAB_IFACE" --bssid "$LAB_BSSID" --channel "$LAB_CHANNEL" "${@:2}"
}
```

## Exercises

| Mode | Lab setup | Evidence |
| --- | --- | --- |
| `sniff` | AP on the specified channel. Add `--inject-test` for the adapter injection check, which can send probe frames. | AP metadata, observed station addresses, and a packet capture. |
| `hidden` | Hide the SSID and reconnect the lab client during capture. | Hidden beacon and SSID from association or probe-response frames. |
| `mac-filter` | Open AP with a MAC allow list. Disconnect the allow-listed client before using its address on the second adapter. | Association outcomes before and after the address change. |
| `wep-replay` | WEP with shared-key authentication. Reconnect the lab client during capture. | Captured keystream and the association result from replay. |
| `wep` | WEP with client traffic. With `--arp-replay`, the supplied client must be observed on the AP. | Target capture and key recovery result. |
| `wpa` | WPA/WPA2-Personal. Reconnect the lab client during capture. | Verified handshake and optional wordlist result. |
| `twin` | WPA/WPA2-Personal and a second radio. Make the original AP unavailable to the test client after JAMES identifies it. | Handshake from the allow-listed lab client's connection attempt and optional wordlist result. |
| `wpa3` | WPA3 or WPA2/WPA3 transition mode. For a transition test, reconnect a WPA2 client or supply a second radio for the WPA2 twin. | Beacon AKM classification, plus WPA2 evidence when available in transition mode. |
| `traffic` | WPA2-Personal, the lab passphrase, a second radio, and an existing Linux lab bridge with DHCP and an upstream connection. | Ethernet capture filtered to the lab client and a packet count. |

```bash
lab hidden --client "$LAB_CLIENT"
lab mac-filter --client "$LAB_CLIENT" --client-interface "$LAB_SECOND_IFACE"
lab wep-replay --client "$LAB_CLIENT"
lab wep --client "$LAB_CLIENT" --arp-replay
lab wpa --client "$LAB_CLIENT" --wordlist "$LAB_WORDLIST"
lab twin --client "$LAB_CLIENT" --ap-interface "$LAB_SECOND_IFACE" \
  --country US --wordlist "$LAB_WORDLIST"
lab wpa3
lab wpa3 --client "$LAB_CLIENT" --ap-interface "$LAB_SECOND_IFACE" \
  --country US --wordlist "$LAB_WORDLIST"
lab traffic --client "$LAB_CLIENT" --ap-interface "$LAB_SECOND_IFACE" \
  --country US --bridge br-lab
```

Use your local country code. `--deauth` sends one five-frame burst to `--client` after JAMES sees that station on the specified BSSID. It applies to `hidden`, `wep`, `wep-replay`, and `wpa`. In the twin exercises, reconnect the lab client after the second AP is ready. WPA3-only reports the observed SAE configuration. Transition mode tests the WPA2 side. Client behavior and management-frame protection affect which exchanges appear in the capture.

For `traffic`, the bridge supplies the lab's routing and DHCP. Hostapd attaches the test AP to that bridge and allows the specified client. Enter the passphrase at the terminal or pass a prior run's key with `--key-file`. Generate traffic from the lab client during the capture window and inspect `traffic.pcap` with Wireshark.

## Results

Each invocation saves a private run directory beneath `~/.james/loot/wifi-lab` for the account running the command. With `sudo` that is normally root. Use `--output-dir` to choose the parent directory. The terminal and `report.json` report the evidence path, observed results, and any cleanup error. Recovered keys are written to `recovered-key.txt` inside that run directory.

Set `--seconds` to extend the capture window and `--crack-seconds` to extend key recovery. Exit codes are `0` for observed evidence, `1` when expected evidence or a key was absent, `2` for a setup, execution, or cleanup error, and `130` on interruption. Ctrl+C stops the run and triggers adapter restoration.
