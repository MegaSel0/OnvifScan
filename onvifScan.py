import socket
import subprocess
import re
import json
from onvif import ONVIFCamera
import cv2
import os
import sys
import time

start_time = time.time()

def get_local_ips():
    result = subprocess.run(['ip', '-4', 'addr'], capture_output=True, text=True)
    ip_pattern = r'inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    ips = re.findall(ip_pattern, result.stdout)
    return ips

def discover_onvif_devices(ip_range, timeout=5):
    UDP_PORT = 3702
    responses = []

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    discovery_msg = (
        b"<?xml version='1.0' encoding='UTF-8'?>"
        b"<e:Envelope xmlns:e='http://www.w3.org/2003/05/soap-envelope' xmlns:w='http://schemas.xmlsoap.org/ws/2004/08/addressing' xmlns:d='http://schemas.xmlsoap.org/ws/2005/04/discovery' xmlns:dn='http://www.onvif.org/ver10/network/wsdl'>"
        b"<e:Header>"
        b"<w:MessageID>uuid:12345678-1234-1234-1234-123456789abc</w:MessageID>"
        b"<w:To>urn:schemas-xmlsoap-org:ws:2005:04/discovery</w:To>"
        b"<w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>"
        b"</e:Header>"
        b"<e:Body>"
        b"<d:Probe>"
        b"<d:Types>dn:NetworkVideoTransmitter</d:Types>"
        b"</d:Probe>"
        b"</e:Body>"
        b"</e:Envelope>"
    )

    sock.sendto(discovery_msg, (f'{ip_range}.255', UDP_PORT))
    sock.settimeout(timeout)

    try:
        while True:
            try:
                data, addr = sock.recvfrom(4096)
                responses.append(f"Discovered device at {addr[0]}: {data}")
            except socket.timeout:
                break
    finally:
        sock.close()

    return responses

def extract_ip_addresses(output):
    pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    ip_addresses = re.findall(pattern, output)
    return ip_addresses

def get_rtsp_link_onvif(ip, port=80, username="admin", password=""):
    try:
        cam = ONVIFCamera(ip, port, username, password)
        cam.update_xaddrs()
        media_service = cam.create_media_service()
        profiles = media_service.GetProfiles()
        profile = profiles[0]
        stream_uri = media_service.GetStreamUri({'StreamSetup': {'Stream': 'RTP-Unicast', 'Transport': 'RTSP'}, 'ProfileToken': profile.token})

        rtsp_link = stream_uri.Uri

        parsed_url = re.match(r"rtsp://[^:]+:(\d+)", rtsp_link)
        if parsed_url:
            rtsp_port = parsed_url.group(1)
        else:
            rtsp_port = port 

        rtsp_path = rtsp_link.split('/', 3)[-1]
        rtsp_with_port = f"{rtsp_port}/{rtsp_path}"
        return rtsp_link, rtsp_with_port  
    except Exception as e:
        return f"Error: {str(e)}", None

def check_rtsp_stream(rtsp_link):
    devnull = open(os.devnull, 'w')
    old_stderr = sys.stderr
    sys.stderr = devnull
    try:
        cap = cv2.VideoCapture(rtsp_link)
        success = cap.isOpened()
        cap.release()
        return success
    except Exception:
        return False
    finally:
        sys.stderr = old_stderr
        devnull.close()

def update_json_file(device_data):
    file_path = 'onvif_devices.json'

    if os.path.exists(file_path):
        with open(file_path, 'r') as json_file:
            try:
                devices = json.load(json_file)
            except json.JSONDecodeError:
                devices = []
    else:
        devices = []

    current_devices_dict = {device['ip']: device for device in devices}
    new_devices_dict = {new_device['ip']: new_device for new_device in device_data}
    for ip, new_device in new_devices_dict.items():
        current_devices_dict[ip] = new_device
    current_devices_dict = {ip: device for ip, device in current_devices_dict.items() if ip in new_devices_dict}
    with open(file_path, 'w') as json_file:
        json.dump(list(current_devices_dict.values()), json_file, indent=4, ensure_ascii=False)

def main():
    local_ips = get_local_ips()
    seen_ips = set()
    device_data = []

    for ip in local_ips:
        ip_range = '.'.join(ip.split('.')[:-1])
        responses = discover_onvif_devices(ip_range)
        
        if responses:
            all_ips = []
            for response in responses:
                ip_addresses = extract_ip_addresses(response)
                all_ips.extend(ip_addresses)

            unique_ips = list(set(all_ips))
            for ip in unique_ips:
                if ip not in seen_ips: 
                    seen_ips.add(ip)  
                    rtsp_link, rtsp_path = get_rtsp_link_onvif(ip)

                    device_info = {
                        "ip": ip,
                        "rtsp_link": rtsp_link,
                        "access": "open" if check_rtsp_stream(rtsp_link) else "close",
                        "rtsp": rtsp_path
                    }

                    if 'Error' in rtsp_link:
                        device_info["access"] = "error"

                    device_data.append(device_info)

    update_json_file(device_data)

    print(json.dumps(device_data, indent=4))

    elapsed_time = time.time() - start_time
    print(f"--- {elapsed_time:.2f} seconds ---")


if __name__ == "__main__":
    main()
