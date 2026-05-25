[app]
title = MoviesDA App
package.name = moviesdaapp
package.domain = org.example
source.dir = .
source.include_exts = py,kv,json,md
version = 0.1
requirements = python3,kivy,kivymd,requests,beautifulsoup4
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

[buildozer]
log_level = 2
warn_on_root = 1
