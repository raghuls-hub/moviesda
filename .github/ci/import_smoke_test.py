#!/usr/bin/env python3
import sys, types, traceback
sys.path.insert(0, 'src')

# Lightweight mocks for GUI frameworks so imports succeed in CI
kivy = types.ModuleType('kivy')
kivy.clock = types.ModuleType('kivy.clock')
kivy.clock.Clock = object
kivy.app = types.ModuleType('kivy.app')
kivy.app.App = object
kivy.uix = types.ModuleType('kivy.uix')
kivy.properties = types.ModuleType('kivy.properties')
sys.modules['kivy'] = kivy
sys.modules['kivy.clock'] = kivy.clock
sys.modules['kivy.app'] = kivy.app

# Provide kivy.lang.Builder used by the app
kivy.lang = types.ModuleType('kivy.lang')
def _dummy_builder(src=None):
    return None
kivy.lang.Builder = _dummy_builder
sys.modules['kivy.lang'] = kivy.lang

# Mock ScreenManager used by the app
kivy.uix.screenmanager = types.ModuleType('kivy.uix.screenmanager')
kivy.uix.screenmanager.ScreenManager = object
class Screen:
    def __init__(self, *a, **k):
        pass
kivy.uix.screenmanager.Screen = Screen
sys.modules['kivy.uix.screenmanager'] = kivy.uix.screenmanager

# metrics
kivy.metrics = types.ModuleType('kivy.metrics')
def _dp(x):
    return x
kivy.metrics.dp = _dp
sys.modules['kivy.metrics'] = kivy.metrics

# image and progressbar
kivy.uix.image = types.ModuleType('kivy.uix.image')
class AsyncImage:
    def __init__(self, *a, **k):
        pass
kivy.uix.image.AsyncImage = AsyncImage
sys.modules['kivy.uix.image'] = kivy.uix.image

kivy.uix.progressbar = types.ModuleType('kivy.uix.progressbar')
class ProgressBar:
    def __init__(self, *a, **k):
        pass
kivy.uix.progressbar.ProgressBar = ProgressBar
sys.modules['kivy.uix.progressbar'] = kivy.uix.progressbar

# Minimal kivymd.uix mocks used by screens.py
kivymd = types.ModuleType('kivymd')
sys.modules['kivymd'] = kivymd
kivymd.uix = types.ModuleType('kivymd.uix')
sys.modules['kivymd.uix'] = kivymd.uix

box = types.ModuleType('kivymd.uix.boxlayout')
class MDBoxLayout:
    def __init__(self, *a, **k):
        pass
    def add_widget(self, *a, **k):
        pass
box.MDBoxLayout = MDBoxLayout
sys.modules['kivymd.uix.boxlayout'] = box

button = types.ModuleType('kivymd.uix.button')
class MDButton:
    def __init__(self, *a, **k):
        self.disabled = False
    def add_widget(self, *a, **k):
        pass
    def bind(self, *a, **k):
        pass
class MDButtonText:
    def __init__(self, *a, **k):
        pass
class MDIconButton(MDButton):
    pass
button.MDButton = MDButton
button.MDButtonText = MDButtonText
button.MDIconButton = MDIconButton
sys.modules['kivymd.uix.button'] = button

card = types.ModuleType('kivymd.uix.card')
class MDCard:
    def __init__(self, *a, **k):
        pass
    def add_widget(self, *a, **k):
        pass
card.MDCard = MDCard
sys.modules['kivymd.uix.card'] = card

label = types.ModuleType('kivymd.uix.label')
class MDLabel:
    def __init__(self, *a, **k):
        pass
    def __repr__(self):
        return '<MDLabel>'
label.MDLabel = MDLabel
sys.modules['kivymd.uix.label'] = label

kivymd.app = types.ModuleType('kivymd.app')
kivymd.app.MDApp = object
sys.modules['kivymd.app'] = kivymd.app

try:
    import moviesda_app.main as app
    print('import moviesda_app.main ok')
except Exception:
    traceback.print_exc()
    raise
