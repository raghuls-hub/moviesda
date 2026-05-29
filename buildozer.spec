[app]
# (str) Title of your application
title = MoviesDA

# (str) Package name
package.name = moviesda

# (str) Package domain
package.domain = org.moviesda

# (str) Source code where the main.py lives
source.dir = moviesda_app

# (list) Source files to include
source.include_exts = py,kv,png,jpg,jpeg,webp,atlas,ttf,otf,mp3,wav,ogg

# (list) Source files to exclude
source.exclude_dirs = .git,.venv,.vscode,__pycache__,build,dist,.pytest_cache

# (str) Application version
version = 0.1.0

# (str) Application entry point
entrypoint = main.py

# (list) Application requirements
# KivyMD 2.x is required because the app uses MDButton and MDButtonText.
requirements = python3,kivy,requests,beautifulsoup4,plyer,kivymd @ https://github.com/kivymd/KivyMD/archive/master.zip

# (list) Permissions
android.permissions = INTERNET,POST_NOTIFICATIONS,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# (int) Target Android API
android.api = 34

# (int) Minimum Android API
android.minapi = 24

# (int) Android NDK API
android.ndk_api = 24

# (list) Android architectures
android.archs = arm64-v8a, armeabi-v7a

# (bool) Automatically accept Android SDK licenses in CI
android.accept_sdk_license = True

# (str) App orientation
orientation = portrait

[buildozer]
# (int) Log level
log_level = 2

# (int) Warn when running as root
warn_on_root = 1
