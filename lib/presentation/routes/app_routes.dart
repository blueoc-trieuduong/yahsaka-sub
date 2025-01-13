import 'package:flutter/material.dart';

import '../presentation.dart';
import 'routes.dart';

class AppRoutes {
  AppRoutes._();

  static final navigatorKey = GlobalKey<NavigatorState>();
  static Map<String, WidgetBuilder> routes = {};

  static Route<dynamic>? onGenerateRoute(RouteSettings settings) {
    WidgetBuilder? builder;
    // final arguments = settings.arguments;
    final uri = Uri.tryParse(settings.name ?? '');
    if (uri == null || uri.path.isEmpty) return null;

    switch (uri.path) {
      case Routes.splash:
        builder = (context) => const SplashScreen();
        break;
      case Routes.home:
        builder = (context) => const HomeScreen();
        break;
      default:
        break;
    }
    if (builder != null) {
      return MaterialPageRoute(settings: settings, builder: builder);
    }
    return null;
  }
}
