import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import 'package:share_plus/share_plus.dart';

import '../core/api_client.dart';
import '../core/session.dart';
import 'note_create_screen.dart';

class HomeScreen extends StatefulWidget {
	const HomeScreen({super.key});

	@override
	State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
	List<dynamic> _notes = [];
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
		safeSetState(() {
			_loading = true;
			_error = null;
		});
		try {
			final resp = await _api.dio.get('/notes');
			if (!mounted) return;
			safeSetState(() {
				_notes = (resp.data as List);
			});
		} on DioException catch (e) {
			safeSetState(() {
				_error = e.response?.data?.toString() ?? 'Failed to load';
			});
		} finally {
			safeSetState(() => _loading = false);
		}
	}

	Future<void> _shareNote(String id) async {
		try {
			final resp = await _api.dio.post('/notes/$id/share_summary');
			final text = (resp.data as Map<String, dynamic>)['text'] as String?;
			if (text != null && text.isNotEmpty) {
				await Share.share(text);
			}
		} catch (_) {}
	}

	Future<void> _markDone(String id) async {
		try {
			await _api.dio.post('/notes/$id/status', data: { 'status': 'done' });
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
			appBar: AppBar(title: const Text('Second Brain')),
			body: _loading
					? const Center(child: CircularProgressIndicator())
					: _error != null
							? Center(child: Text(_error!))
							: RefreshIndicator(
								onRefresh: _load,
								child: ListView.separated(
									padding: const EdgeInsets.all(12),
									itemBuilder: (context, i) {
										final n = _notes[i] as Map<String, dynamic>;
										final id = n['id'] as String;
										final status = (n['status'] as String?) ?? '';
										return ListTile(
											title: Text(n['text'] ?? '(no text)'),
											subtitle: Text('Status: $status'),
											trailing: Wrap(spacing: 8, children: [
												IconButton(
													onPressed: () => _shareNote(id),
													icon: const Icon(Icons.ios_share),
													tooltip: 'Share',
												),
												IconButton(
													onPressed: status == 'done' ? null : () => _markDone(id),
													icon: const Icon(Icons.check_circle_outline),
													tooltip: 'Mark done',
												),
											]),
										);
								},
								separatorBuilder: (_, __) => const Divider(height: 1),
								itemCount: _notes.length,
							),
						),
			floatingActionButton: FloatingActionButton.extended(
				onPressed: () async {
					await Navigator.of(context).push(MaterialPageRoute(builder: (_) => const NoteCreateScreen()));
					if (mounted) _load();
				},
				label: const Text('Add note'),
				icon: const Icon(Icons.add),
			),
		);
	}
}
