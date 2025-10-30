import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

class Session extends ChangeNotifier {
	static const _kAccessTokenKey = 'access_token'; //const means this variable is immutable and cannot be changed
	final FlutterSecureStorage _secure = const FlutterSecureStorage();
	String? _accessToken;

	bool get isAuthenticated => _accessToken != null && _accessToken!.isNotEmpty;
	String? get accessToken => _accessToken;

	Future<void> load() async {
		_accessToken = await _secure.read(key: _kAccessTokenKey);
		notifyListeners();
	}

	Future<void> setToken(String token) async {
		_accessToken = token;
		await _secure.write(key: _kAccessTokenKey, value: token);
		notifyListeners();
	}

	Future<void> logout() async {
		_accessToken = null;
		await _secure.delete(key: _kAccessTokenKey);
		notifyListeners();
	}
}
