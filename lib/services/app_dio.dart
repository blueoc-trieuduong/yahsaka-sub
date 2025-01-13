import 'package:dio/dio.dart';
import 'package:injectable/injectable.dart';
import 'package:yahsaka_timesheet/app/config/app_config.dart';

@singleton
class AppDio {
  final Dio _dio = Dio();

  Dio get dio => _dio;

  AppDio() {
    _dio
      ..options.baseUrl = AppConfig.baseUrl
      ..options.connectTimeout = const Duration(milliseconds: 10000);
  }
}
