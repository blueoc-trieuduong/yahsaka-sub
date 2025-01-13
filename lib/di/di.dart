import 'package:get_it/get_it.dart';
import 'package:injectable/injectable.dart';

import 'di.config.dart';

final locator = GetIt.instance..allowReassignment = true;

Future<void> configureAllDependencies() async {
  configureDependencies();

  await locator.allReady();
}

@InjectableInit()
void configureDependencies() => locator.init();
