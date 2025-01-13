import 'package:flutter/material.dart';
import 'package:yahsaka_timesheet/app/config/app_config.dart';

import 'app/app.dart';
import 'di/di.dart';

void main() async {
  AppConfig.setup(Environment.dev);
  await configureAllDependencies();
  runApp(const MyApp());
}
