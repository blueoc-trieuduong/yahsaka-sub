enum Environment { dev, prod }

class AppConfig {
  AppConfig._();

  static late Environment environment;

  static late Map<String, dynamic> _config;

  static String baseUrl = _config[_Config.baseUrl];

  static bool get isDevelop => environment == Environment.dev;

  static bool get isProduction => environment == Environment.prod;

  static void setup(Environment env) {
    environment = env;
    switch (env) {
      case Environment.dev:
        _config = _Config.devConstants;
        break;
      case Environment.prod:
        _config = _Config.prodConstants;
        break;
    }
  }
}

class _Config {
  static const baseUrl = 'BASE_URL';

  static Map<String, dynamic> devConstants = {
    baseUrl: 'https://example.abc',
  };

  static Map<String, dynamic> prodConstants = {
    baseUrl: 'https://example.abc',
  };
}
