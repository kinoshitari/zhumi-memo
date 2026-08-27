[app]
title = 猪咪备忘录
project_dir = .
input_file = android_app/main.py
exec_directory = android_app
project_file = android_app/zhumi_android.pyproject
icon = assets/android_icon_512.png

[python]
python_path =
packages =
android_packages = buildozer==1.5.0,cython==0.29.33

[qt]
qml_files =
excluded_qml_plugins =

[android]
wheel_pyside =
wheel_shiboken =
plugins = platforms_qtforandroid

[nuitka]
extra_args = --quiet

[buildozer]
mode = debug
recipe_dir =
jars_dir =
ndk_path =
sdk_path =
modules = Core,Gui,Widgets
local_libs = plugins_platforms_qtforandroid
arch = aarch64
