import subprocess
import pathlib
import os
from datetime import datetime
import xml.etree.ElementTree as ET
import json

def getProp(prop):
    cmd = "adb shell getprop " + prop
    p = subprocess.run(cmd, stdout=subprocess.PIPE).stdout.decode('utf-8').rstrip()
    return p

def getPackageInfo(prop):
    cmd = "adb shell dumpsys package com.instagram.android | grep " + prop
    p = subprocess.run(cmd, stdout=subprocess.PIPE).stdout.decode('utf-8').split("=")[1].rstrip()
    return p

def pullFile(path, _cwd):
    subprocess.run(f"adb pull /data/data/com.instagram.android/{path}", cwd=_cwd)

device_name = getProp("ro.product.manufacturer").capitalize() + " " + getProp("ro.product.model")

result_path = pathlib.Path(__file__).parent.resolve()/"result"
if not os.path.exists(result_path):
    os.makedirs(result_path)

current_time = datetime.now().strftime("%Y_%m_%d-%I_%M_%S_%p")
current_path = result_path/f"{device_name} {current_time}"
os.makedirs(current_path)

pullFile("shared_prefs/com.instagram.android_preferences.xml", current_path)
pullFile("databases/direct.db", current_path)
pullFile("cache/images.stash/clean", current_path)

print(f"""Manufacturer: {getProp("ro.product.manufacturer").capitalize()}
Model: {getProp("ro.product.model")}
Device Name: {device_name}
Android Version: {getProp("ro.build.version.release")}
Android SDK: {getProp("ro.build.version.sdk")}
Serial Number: {getProp("ro.serialno")}
Rooted: {"Yes" if getProp("service.adb.root") else "No"}
""")

print(f"""Instagram
Version: {getPackageInfo("versionName")}
Installed by: {getPackageInfo("installerPackageName")}
First Installed: {getPackageInfo("firstInstallTime")}
Last Updated: {getPackageInfo("lastUpdateTime")}
""")



os.makedirs(current_path/"processed"/"clean")
for filename in os.listdir(current_path/"clean"):
    os.rename(current_path/"clean"/filename, current_path/"processed"/"clean"/f"{filename}.jpg")

root = ET.parse(current_path/'com.instagram.android_preferences.xml').getroot()

uam = {}
for child in root.findall('string'):
    if child.attrib['name'] == 'user_access_map':
        uam = json.loads(child.text)

print(f"""Full Name: {uam[0]["user_info"]["full_name"]}
Username: {uam[0]["user_info"]["username"]}
Profile Picture: {uam[0]["user_info"]["profile_pic_url"]}
Biography: {uam[0]["user_info"]["biography"]}
Last Active: {datetime.fromtimestamp(uam[0]["time_accessed"]/1000.0).strftime("%c")}
""")