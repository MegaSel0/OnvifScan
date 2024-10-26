## The camera scanning program is built based on the ONVIF structure. This program can scan all ONVIF cameras in the local network and return the cameras that comply with the ONVIF standard.

![onvif](https://github.com/user-attachments/assets/5250af85-fa04-4ed3-b3e5-a39dda14653f)



# Features of this program:

  Scans only cameras in the local network (e.g., organization, home, etc.)
  Scans cameras across all defined range specifications in the system
  Saves details such as the camera's IP, RTSP link, access, and RTSP information to a JSON output file
  If you provide the IP, username, and password, it will also return the RTSP details for closed-circuit cameras

## Note:
The scanning process may take some time, depending on the defined ranges in your system,
as it scans all specified IP ranges. Additionally, please note that for the program to return camera
details, the IP range of your system must match the camera's range. Finally, after the program
completes its work, the output will be saved in a file named onvif_devices.json.

## Prerequisites and Installation Guide for the Library: ->  pip install onvif-zeep opencv-python
```bash
 pip install onvif-zeep opencv-python
```
## if needed: -> install python3


