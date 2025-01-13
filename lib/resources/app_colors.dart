import 'package:flutter/material.dart';

class AppColors {
  static const primary = Color(0xFF3C84F0);

  final Color buttonPrimary;
  final Color buttonSecondary;
  final Color primaryBackground;
  final Color textPrimary;
  final Color textSecondary;
  final Color iconPrimary;
  final Color iconSecondary;
  final Color border;

  AppColors({
    required this.buttonPrimary,
    required this.buttonSecondary,
    required this.primaryBackground,
    required this.textPrimary,
    required this.textSecondary,
    required this.iconPrimary,
    required this.iconSecondary,
    required this.border,
  });
}

AppColors lightAppColors = AppColors(
  buttonPrimary: const Color(0xFF3C84F0),
  iconPrimary: const Color(0xFF3C84F0),
  iconSecondary: const Color(0xFFBEC7D8),
  buttonSecondary: const Color(0xFF0A84FF),
  primaryBackground: const Color(0xFF010A1F),
  textPrimary: const Color(0xFFFFFFFF),
  textSecondary: const Color(0xFF9CA4AF),
  border: const Color(0xFFBEC7D8),
);

AppColors darkAppColors = AppColors(
  buttonPrimary: const Color(0xFF3C84F0),
  iconPrimary: const Color(0xFF3C84F0),
  iconSecondary: const Color(0xFFBEC7D8),
  buttonSecondary: const Color(0xFF0A84FF),
  primaryBackground: const Color(0xFF010A1F),
  textPrimary: const Color(0xFFFFFFFF),
  textSecondary: const Color(0xFF9CA4AF),
  border: const Color(0xFFBEC7D8),
);

extension AppColorsExtension on BuildContext {
  AppColors get colors =>
      MediaQuery.platformBrightnessOf(this) == Brightness.dark
          ? darkAppColors
          : lightAppColors;
}
