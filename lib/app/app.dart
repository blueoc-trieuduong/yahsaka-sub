import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:yahsaka_timesheet/resources/app_colors.dart';

import '../presentation/routes/app_routes.dart';
import '../presentation/routes/routes.dart';

final RouteObserver<ModalRoute> routeObserver = RouteObserver<ModalRoute>();
final RouteObserver<PageRoute> pageRouteObserver = RouteObserver<PageRoute>();

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ProviderScope(
      child: MaterialApp(
        title: 'Yahsaka',
        theme: ThemeData(
          // fontFamily: FontFamily.zenDots,
          colorScheme: ColorScheme.fromSeed(
            seedColor: AppColors.primary,
          ),
        ),
        debugShowCheckedModeBanner: false,
        // locale: state.locale,
        // localizationsDelegates: AppLocalizations.localizationsDelegates,
        // supportedLocales: AppLocalizations.supportedLocales,
        navigatorObservers: [
          routeObserver,
          pageRouteObserver,
        ],
        navigatorKey: AppRoutes.navigatorKey,
        routes: AppRoutes.routes,
        onGenerateRoute: AppRoutes.onGenerateRoute,
        initialRoute: Routes.splash,
        builder: (context, child) {
          if (child == null) return const SizedBox();
          return child;
        },
      ),
    );
  }
}
