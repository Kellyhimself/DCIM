import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';

import '../core/api_client.dart';
import '../core/session.dart';

class ClientsScreen extends StatefulWidget {
	const ClientsScreen({super.key});

	@override
	State<ClientsScreen> createState() => _ClientsScreenState();
}

class _ClientsScreenState extends State<ClientsScreen> {
	List<dynamic> _clients = [];
	bool _loading = true;
	String? _error;

	ApiClient get _api => context.read<ApiClient>();
	Session get _session => context.read<Session>();

	void safeSetState(VoidCallback fn) {
		if (!mounted) return;
		setState(fn);
	}

	Future<void> _load() async {
		_api.attachSession(_session);
		safeSetState(() { _loading = true; _error = null; });
		try {
			final resp = await _api.dio.get('/clients');
			if (!mounted) return;
			safeSetState(() { _clients = resp.data as List; });
		} on DioException catch (e) {
			safeSetState(() { _error = e.response?.data?.toString() ?? 'Failed to load'; });
		} finally {
			safeSetState(() { _loading = false; });
		}
	}

	Future<void> _createClient() async {
		final nameCtrl = TextEditingController();
		final phoneCtrl = TextEditingController();
		final locationCtrl = TextEditingController();
		final ok = await showDialog<bool>(
			context: context,
			builder: (_) => AlertDialog(
				title: const Text('New client'),
				content: Column(
					mainAxisSize: MainAxisSize.min,
					children: [
						TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: 'Name')),
						TextField(controller: phoneCtrl, decoration: const InputDecoration(labelText: 'Phone')),
						TextField(controller: locationCtrl, decoration: const InputDecoration(labelText: 'Location')),
					],
				),
				actions: [
					TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
					FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Save')),
				],
			),
		);
		if (ok != true) return;
		try {
			await _api.dio.post('/clients', data: {
				'name': nameCtrl.text.trim(),
				'phone': phoneCtrl.text.trim(),
				'location': locationCtrl.text.trim(),
			});
			await _load();
		} catch (_) {}
	}

	@override
	void initState() {
		super.initState();
		WidgetsBinding.instance.addPostFrameCallback((_) => _load());
	}

	@override
	Widget build(BuildContext context) {
		return Scaffold(
			appBar: AppBar(title: const Text('Clients')),
			body: _loading
					? const Center(child: CircularProgressIndicator())
					: _error != null
							? Center(child: Text(_error!))
							: RefreshIndicator(
								onRefresh: _load,
								child: ListView.separated(
									padding: const EdgeInsets.all(12),
									itemBuilder: (_, i) {
										final c = _clients[i] as Map<String, dynamic>;
										return ListTile(
											title: Text(c['name'] ?? ''),
											subtitle: Text([c['phone'], c['location']].whereType<String>().where((s) => s.isNotEmpty).join(' • ')),
										);
									},
									separatorBuilder: (_, __) => const Divider(height: 1),
									itemCount: _clients.length,
							),
						),
			floatingActionButton: FloatingActionButton.extended(
				onPressed: _createClient,
				label: const Text('Add'),
				icon: const Icon(Icons.person_add_alt),
			),
		);
	}
}
