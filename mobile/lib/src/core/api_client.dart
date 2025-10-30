import 'package:dio/dio.dart';

import 'session.dart';

class ApiClient {
	final Dio dio = Dio(
		BaseOptions(
			baseUrl: const String.fromEnvironment(
				'API_BASE_URL',
				defaultValue: 'http://localhost:8080',
			),
			connectTimeout: const Duration(seconds: 15),
			receiveTimeout: const Duration(seconds: 20),
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
