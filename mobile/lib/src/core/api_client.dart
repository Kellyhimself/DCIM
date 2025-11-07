import 'package:dio/dio.dart';

import 'session.dart';

class ApiClient {
	final Dio dio = Dio(
		BaseOptions(
			baseUrl: const String.fromEnvironment(
				'API_BASE_URL',
				defaultValue: 'http://192.168.1.105:8080',
			),
			connectTimeout: const Duration(seconds: 30),
			receiveTimeout: const Duration(seconds: 30),
			headers: {
				'Content-Type': 'application/json',
			},
		),
	);

	void attachSession(Session session) {
		dio.interceptors.clear();
		dio.interceptors.add(
			InterceptorsWrapper(
				onRequest: (options, handler) {
					final token = session.accessToken;
					if (token != null && token.isNotEmpty) {
						options.headers['Authorization'] = 'Bearer $token';
					}
					return handler.next(options);
				},
			),
		);
	}
}