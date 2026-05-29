[app]
title = MoviesDA
package.name = moviesda
package.domain = org.example
source.dir = .
source.include_exts = py,kv,png,jpg,atlas,ttf,otf,txt,json
version = 0.1.0
requirements = python3,kivy==2.3.1,requests,beautifulsoup4,plyer,kivymd @ git+https://github.com/kivymd/KivyMD.git@master
orientation = portrait
fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 1

[android]
# Android API/NDK settings
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = armeabi-v7a,arm64-v8a
android.compile_sdk = 33

# Permissions required by the app
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,ACCESS_NETWORK_STATE,WAKE_LOCK

# If you need to sign the build, configure these, otherwise Buildozer will create a debug key
# android.release_keyalias = mykey
# android.release_keystore = /path/to/keystore
# android.release_keystore_passwd = secret
# android.release_keyalias_passwd = secret

# Notes:
# - KivyMD is pulled from the git URL above. If pip install of the git URL fails during p4a
#   build, either vendor KivyMD into your project or create a p4a recipe for the required KivyMD commit.
# - Building for Android is best performed on Linux/WSL2. Windows hosts are not officially supported
#   for the full Android toolchain. See https://buildozer.readthedocs.io/ and https://python-for-android.readthedocs.io/
[app]
title = MoviesDA App
package.name = moviesdaapp
package.domain = org.moviesda
source.dir = .
source.include_exts = py,kv,json,md,png,jpg,jpeg,gif,webp
version = 0.1

requirements = python3,kivy,kivymd,requests,beautifulsoup4,plyer,certifi,charset-normalizer,idna,urllib3,soupsieve

# make src/ package importable on Android
android.add_src = src

orientation = portrait
fullscreen = 0

android.api = 33
android.minapi = 26
android.ndk = 25b
android.build_tools_version = 33.0.2
android.archs = arm64-v8a, armeabi-v7a
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,FOREGROUND_SERVICE,POST_NOTIFICATIONS
android.allow_backup = False

# Use patched local recipe to fix libthorvg IndexError
p4a.local_recipes = ./p4a_recipes

p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 1
