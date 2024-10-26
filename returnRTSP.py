#--------------------------------------------Document---------------------------------------------------------|

#To run this program and retrieve the RTSP link from the camera, you should execute it as follows:
# python returnRTSP.py [IP] [Username] [Password]
#--------------------------------------------------------------------------------------------------------------
#For example:
# python returnRTSP.py 192.168.1.10 admin 12345
#--------------------------------------------------------------------------------------------------------------
# Replace:

#     [IP] with the camera’s IP address
#     [Username] with the camera’s username
#     [Password] with the camera’s password

#--------------------------------------------------------------------------------------------------------------

import re
import json
from onvif import ONVIFCamera
import cv2
import os
import sys
import time
from concurrent import futures
import argparse  

start_time = time.time()

def get_rtsp_link_onvif(ip, port=80, username="admin", password=None):
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

def update_json_file(device_info):
    file_path = 'onvif_devices.json'
    
    if os.path.exists(file_path):
        with open(file_path, 'r') as json_file:
            try:
                devices = json.load(json_file)
            except json.JSONDecodeError:
                devices = []  
    else:
        devices = []

    updated = False
    for i, device in enumerate(devices):
        if device.get("ip") == device_info["ip"]:
            devices[i] = device_info  
            updated = True
            break

    if not updated:
        devices.append(device_info) 

    with open(file_path, 'w') as json_file:
        json.dump(devices, json_file, indent=4, ensure_ascii=False)

def main(ip, username, password):
    rtsp_link, rtsp_path = get_rtsp_link_onvif(ip, username=username, password=password)

    device_info = {
        "ip": ip,
        "rtsp_link": rtsp_link,
        "access": "open" if check_rtsp_stream(rtsp_link) else "close",
        "rtsp": rtsp_path  
    }

    if 'Error' in rtsp_link:
        device_info["access"] = "error"

    print(json.dumps(device_info, indent=4))  

    update_json_file(device_info)

    elapsed_time = time.time() - start_time
    print(f"--- {elapsed_time:.2f} seconds ---")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get RTSP link from ONVIF camera.')
    parser.add_argument('ip', type=str, help='IP address of the camera')
    parser.add_argument('user', type=str, help='Username for the camera')
    parser.add_argument('password', type=str, help='Password for the camera')

    args = parser.parse_args()

    main(args.ip, args.user, args.password)
