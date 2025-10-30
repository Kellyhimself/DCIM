import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';

import '../core/api_client.dart';
import '../core/session.dart';

class SearchScreen extends StatefulWidget {
	const SearchScreen({super.key});

	@override
	State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
	final _qCtrl = TextEditingController();
	List<dynamic> _clients = [];
	List<dynamic> _jobs = [];
	List<dynamic> _notes = [];
	bool _loading = false;
	String? _error;

	ApiClient get _api => context.read<ApiClient>();
	Session get _session => context.read<Session>();

	Future<void> _run() async {
		_api.attachSession(_session);
		setState(() { _loading = true; _error = null; });
		try {
			final q = _qCtrl.text.trim();
			final res = await Future.wait([
				_api.dio.get('/search/clients', queryParameters: {'q': q}),
				_api.dio.get('/search/jobs', queryParameters: {'q': q}),
				_api.dio.get('/search/notes', queryParameters: {'q': q}),
			]);
			setState(() {
				_clients = res[0].data as List;
				_jobs = res[1].data as List;
				_notes = res[2].data as List;
			});
		} on DioException catch (e) {
			setState(() { _error = e.response?.data?.toString() ?? 'Search failed'; });
		} finally {
			setState(() { _loading = false; });
		}
	}

	@override
	Widget build(BuildContext context) {
		return Scaffold(
			appBar: AppBar(title: const Text('Search')),
			body: Padding(
				padding: const EdgeInsets.all(12),
				child: Column(
					children: [
						Row(children: [
							Expanded(child: TextField(controller: _qCtrl, decoration: const InputDecoration(hintText: 'Search...'))),
							const SizedBox(width: 8),
							FilledButton(onPressed: _loading ? null : _run, child: const Text('Go')),
						]),
						const SizedBox(height: 12),
						if (_error != null) Text(_error!, style: const TextStyle(color: Colors.red)),
						Expanded(
							child: ListView(
								children: [
									const Text('Clients', style: TextStyle(fontWeight: FontWeight.bold)),
									..._clients.map((c) => ListTile(title: Text(c['name'] ?? ''), subtitle: Text((c['phone'] ?? '') as String))).toList(),
									const SizedBox(height: 8),
									const Text('Jobs', style: TextStyle(fontWeight: FontWeight.bold)),
									..._jobs.map((j) => ListTile(title: Text(j['site'] ?? ''), subtitle: Text('Status: ${j['status']}'))).toList(),
									const SizedBox(height: 8),
									const Text('Notes', style: TextStyle(fontWeight: FontWeight.bold)),
									..._notes.map((n) => ListTile(title: Text(n['text'] ?? ''), subtitle: Text('Status: ${n['status']}'))).toList(),
								],
							),
						),
					],
				),
			),
		);
	}
}
