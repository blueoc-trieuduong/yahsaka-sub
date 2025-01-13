# Yahsaka Timesheet

A scan QR app

## How to run

flutter pub get  
dart run build_runner build -d  
VSCode: Run and Debug  
Cmdline:  
- dev: flutter run -t lib/main_dev.dart
- prod: flutter run

## FVM Usage (optional setup)

- install fvm
- dart pub global activate fvm
- export PATH="$PATH":"$HOME/.pub-cache/bin" (ios), android: add to path
- fvm list
- fvm use 3.27.1
