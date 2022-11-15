import sqlite3
import subprocess
import pathlib
import os
from datetime import datetime
from mdutils.mdutils import MdUtils
from mdutils import Html
import json
import xml.etree.ElementTree as ET
import shutil

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

print("""
  _____           _                                    ______                       _      
 |_   _|         | |                                  |  ____|                     (_)     
   | |  _ __  ___| |_ __ _  __ _ _ __ __ _ _ __ ___   | |__ ___  _ __ ___ _ __  ___ _  ___ 
   | | | '_ \/ __| __/ _` |/ _` | '__/ _` | '_ ` _ \  |  __/ _ \| '__/ _ \ '_ \/ __| |/ __|
  _| |_| | | \__ \ || (_| | (_| | | | (_| | | | | | | | | | (_) | | |  __/ | | \__ \ | (__ 
 |_____|_| |_|___/\__\__,_|\__, |_|  \__,_|_| |_| |_| |_|  \___/|_|  \___|_| |_|___/_|\___|
                            __/ |                                                          
                           |___/                                                           
Note: Make sure your device is rooted and connected to your computer.
This application will extract important instagram data from your device, create a report, and save them in 'result' directory.
""")

print("Press y to continue or any other key to exit.")
answer = input("Do you want to continue? (y/n): ")

if answer != "y":
    exit()
elif not getProp("service.adb.root"):
    print("Your device is not rooted.")
    exit()

investigator = {}

investigator["name"] = input("\nInvestigator Name: ")
investigator["email"] = input("Investigator Email: ")
investigator["phone"] = input("Investigator Phone Number: ")

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

processed_path = current_path/"processed"/"clean"
shutil.copytree(current_path/"clean", processed_path)
for filename in os.listdir(processed_path):
    os.rename(processed_path/filename, processed_path/f"{filename}.jpg")

root = ET.parse(current_path/'com.instagram.android_preferences.xml').getroot()

uam = {}
for child in root.findall('string'):
    if child.attrib['name'] == 'user_access_map':
        uam = json.loads(child.text)

con = sqlite3.connect(current_path/"direct.db")
cur = con.cursor()
threads_sql = cur.execute("SELECT thread_id, thread_info FROM threads")
threads = []

for thread_res in threads_sql.fetchall():
    # print(thread_res[0])
    thread_info = json.loads(thread_res[1])
    participants = {}
    participants[thread_info["inviter"]["user_id"]] = thread_info["inviter"]["username"]
    if thread_info["recipients"]:
        participants[thread_info["recipients"][0]["user_id"]] = thread_info["recipients"][0]["username"]
    # print(participants)
    thread_id = thread_res[0]
    thread = {
        "thread_id": thread_id,
        "participants": participants,
        "messages": []
    }
    msg_sql = cur.execute(f"SELECT user_id, recipient_ids, timestamp, text, message, message_type FROM messages WHERE thread_id='{thread_id}'")
    for msg_res in msg_sql.fetchall():
        msg_time = datetime.fromtimestamp(msg_res[2]/1000000.0).strftime("%c")
        msg_info = json.loads(msg_res[4])
        sender = participants[msg_info["user_id"]] 
        msg_content = ""
        if msg_res[5] == "link":
            msg_content = msg_info["link"]["link_context"]["link_url"]
        else:
            msg_content = msg_res[3]
        # print(f"{sender} {msg_time} {msg_content} {msg_res[5]}")
        thread["messages"].append({
            "sender": sender,
            "time": msg_time,
            "content": msg_content,
            "type": msg_res[5]
            })
    threads.append(thread)

con.close()

mdFile = MdUtils(file_name='Result', title=f"{device_name} {current_time}")

mdFile.new_header(level=1, title='Device Information')

device_info = [
    "Manufacturer", getProp("ro.product.manufacturer").capitalize(),
    "Model", getProp("ro.product.model"),
    "Device Name", device_name,
    "Android Version", getProp("ro.build.version.release"),
    "Android SDK", getProp("ro.build.version.sdk"),
    "Serial Number", getProp("ro.serialno"),
    "Rooted", "Yes" if getProp("service.adb.root") else "No"
]

mdFile.new_table(columns=2, rows=7, text=device_info, text_align='left')

mdFile.new_header(level=1, title='Investigator Information')

device_info = [
    "Investigator Name", investigator["name"],
    "Investigator Email", investigator["email"],
    "Investigator Phone Number", investigator["phone"]
]

mdFile.new_table(columns=2, rows=3, text=device_info, text_align='left')

mdFile.new_header(level=1, title='Instagram Information')

instagram_info = [
    "Version", getPackageInfo("versionName"),
    "Installed by", getPackageInfo("installerPackageName"),
    "First Installed", getPackageInfo("firstInstallTime"),
    "Last Updated", getPackageInfo("lastUpdateTime"),
]

mdFile.new_table(columns=2, rows=4, text=instagram_info, text_align='left')

mdFile.new_header(level=1, title='Account Information')

account_info = [
    "Full Name", uam[0]["user_info"]["full_name"],
    "Username", uam[0]["user_info"]["username"],
    "Profile Picture", uam[0]["user_info"]["profile_pic_url"],
    "Biography", uam[0]["user_info"]["biography"],
    "Last Active", datetime.fromtimestamp(uam[0]["time_accessed"]/1000.0).strftime("%c")
]

mdFile.new_table(columns=2, rows=5, text=account_info, text_align='left')

mdFile.new_header(level=1, title='Conversations')

for i, thread in enumerate(threads):
    mdFile.new_header(level=2, title=f'Conversation {i+1}')
    mdFile.new_table(columns=2, rows=1, text=[
    "Participants", ", ".join(thread["participants"].values()),
], text_align='left')
    msg_md = ["Sender", "Time", "Content", "Type"]
    for msg in thread["messages"]:
        msg_md.extend([msg["sender"], msg["time"], msg["content"], msg["type"]])
    mdFile.new_table(columns=4, rows=len(thread["messages"])+1, text=msg_md, text_align='left')

mdFile.new_header(level=1, title='Images')

for file in os.listdir(processed_path):
     filename = os.fsdecode(file)
     mdFile.new_paragraph(Html.image(path=f"./processed/clean/{filename}", size='200'))

mdFile.new_table_of_contents(table_title='Contents', depth=2)

os.chdir(current_path)
mdFile.create_md_file()

print(f"""
Extracted files and report (Result.md) saved to {current_path
}""")

# ============================== CLI Version ==============================

# print(f"""Manufacturer: {getProp("ro.product.manufacturer").capitalize()}
# Model: {getProp("ro.product.model")}
# Device Name: {device_name}
# Android Version: {getProp("ro.build.version.release")}
# Android SDK: {getProp("ro.build.version.sdk")}
# Serial Number: {getProp("ro.serialno")}
# Rooted: {"Yes" if getProp("service.adb.root") else "No"}
# """)

# print(f"""Instagram
# Version: {getPackageInfo("versionName")}
# Installed by: {getPackageInfo("installerPackageName")}
# First Installed: {getPackageInfo("firstInstallTime")}
# Last Updated: {getPackageInfo("lastUpdateTime")}
# """)

# print(f"""Full Name: {uam[0]["user_info"]["full_name"]}
# Username: {uam[0]["user_info"]["username"]}
# Profile Picture: {uam[0]["user_info"]["profile_pic_url"]}
# Biography: {uam[0]["user_info"]["biography"]}
# Last Active: {datetime.fromtimestamp(uam[0]["time_accessed"]/1000.0).strftime("%c")}
# """)