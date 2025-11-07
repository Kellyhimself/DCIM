import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';

import '../core/api_client.dart';
import '../core/session.dart';
import '../core/app_theme.dart';
import 'root_shell.dart';

class LoginScreen extends StatefulWidget {
	const LoginScreen({super.key});

	@override
	State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
	final _formKey = GlobalKey<FormState>();
	final _emailCtrl = TextEditingController();
	final _passwordCtrl = TextEditingController();
	final _fullNameCtrl = TextEditingController();
	bool _loading = false;
	String? _error;
	bool _isSignup = false;

	Future<void> _submit() async {
		if (!_formKey.currentState!.validate()) return;
		setState(() {
			_loading = true;
			_error = null;
		});
		final api = context.read<ApiClient>();
		final session = context.read<Session>();
		api.attachSession(session);
		try {
			if (_isSignup) {
				// 1) Sign up
				await api.dio.post('/auth/signup', data: {
					'email': _emailCtrl.text.trim(),
					'password': _passwordCtrl.text,
					'full_name': _fullNameCtrl.text.trim().isEmpty ? null : _fullNameCtrl.text.trim(),
				});
			}
			// 2) Login
			final resp = await api.dio.post('/auth/login', data: {
				'email': _emailCtrl.text.trim(),
				'password': _passwordCtrl.text,
			});
			await session.setToken(resp.data['access_token'] as String);
			if (!mounted) return;
			Navigator.of(context).pushReplacement(
				MaterialPageRoute(builder: (_) => const RootShell()),
			);
		} on DioException catch (e) {
			setState(() {
				_error = e.response?.data?.toString() ?? 'Request failed';
			});
		} finally {
			if (mounted) {
				setState(() => _loading = false);
			}
		}
	}

	@override
	Widget build(BuildContext context) {
		return Scaffold(
			body: Center(
				child: ConstrainedBox(
					constraints: const BoxConstraints(maxWidth: 360),
					child: Padding(
						padding: const EdgeInsets.all(16),
						child: Form(
							key: _formKey,
							child: Column(
								mainAxisSize: MainAxisSize.min,
								children: [
									Text(_isSignup ? 'Create account' : 'Second Brain', style: Theme.of(context).textTheme.headlineSmall),
									const SizedBox(height: 16),
									TextFormField(
										controller: _emailCtrl,
										keyboardType: TextInputType.emailAddress,
										decoration: const InputDecoration(labelText: 'Email'),
										validator: (v) => (v == null || v.isEmpty) ? 'Required' : null,
									),
									const SizedBox(height: 12),
									if (_isSignup) ...[
										TextFormField(
											controller: _fullNameCtrl,
											decoration: const InputDecoration(labelText: 'Full name (optional)'),
										),
										const SizedBox(height: 12),
									],
									TextFormField(
										controller: _passwordCtrl,
										decoration: const InputDecoration(labelText: 'Password'),
										obscureText: true,
										validator: (v) => (v == null || v.isEmpty) ? 'Required' : null,
									),
									if (_error != null) ...[
										const SizedBox(height: 12),
										Container(
											padding: const EdgeInsets.all(12),
											decoration: BoxDecoration(
												color: AppColors.deepRed.withOpacity(0.1),
												borderRadius: BorderRadius.circular(8),
												border: Border.all(color: AppColors.deepRed.withOpacity(0.3)),
											),
											child: Row(
												children: [
													Icon(Icons.error_outline, color: AppColors.deepRed, size: 20),
													const SizedBox(width: 8),
													Expanded(
														child: Text(
															_error!,
															style: TextStyle(color: AppColors.deepRed, fontSize: 14),
														),
													),
												],
											),
										),
									],
									const SizedBox(height: 16),
									SizedBox(
										width: double.infinity,
										child: FilledButton(
											onPressed: _loading ? null : _submit,
											child: _loading
												? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
												: Text(_isSignup ? 'Sign up' : 'Login'),
										),
									),
									const SizedBox(height: 12),
									TextButton(
										onPressed: _loading ? null : () => setState(() => _isSignup = !_isSignup),
										child: Text(_isSignup ? 'Have an account? Login' : 'New here? Create account'),
									),
								],
							),
						),
					),
				),
			),
		);
	}
}
