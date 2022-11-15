# instagram-forensic

# Assumption

- Android
- Rooted

# Usage

- Clone this project
- Run `python main.py`

# Sources

| Section               | File path/command                                                                   |
| --------------------- | ----------------------------------------------------------------------------------- |
| Device Information    | adb shell getprop ro.product.manufacturer                                           |
| Instagram Information | adb shell dumpsys package com.instagram.android \| grep versionName                 |
| Account Information   | /data/data/com.instagram.android/shared_prefs/com.instagram.android_preferences.xml |
| Conversations         | /data/data/com.instagram.android/databases/direct.db (threads and messages tables)  |

# Not yet implemented

- Multiple account recognition
- Group chat
