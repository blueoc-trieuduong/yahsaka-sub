import 'package:flutter/material.dart';

import '../routes/routes.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<StatefulWidget> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    initApp();
  }

  void initApp() async {
    // some job
    await Future.delayed(const Duration(seconds: 2));
    navigate();
  }

  void navigate() {
    Navigator.pushReplacementNamed(
      context,
      Routes.home,
    );
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(child: Text('splash')),
    );
  }
}
