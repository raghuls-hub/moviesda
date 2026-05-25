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

p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 1
