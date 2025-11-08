import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import 'package:share_plus/share_plus.dart';

import '../core/api_client.dart';
import '../core/session.dart';
import '../core/app_theme.dart';
import 'voice_capture_screen.dart';
import 'clients_screen.dart';
import 'root_shell.dart';

class HomeScreen extends StatefulWidget {
	const HomeScreen({super.key});

	@override
	State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
	List<dynamic> _notes = [];
	List<dynamic> _clients = [];
	bool _loading = true;
	bool _loadingClients = true;
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

	Future<void> _loadClients() async {
		_api.attachSession(_session);
		safeSetState(() { _loadingClients = true; });
		try {
			final resp = await _api.dio.get('/clients');
			if (!mounted) return;
			safeSetState(() {
				_clients = (resp.data as List);
			});
		} on DioException {
			// Silently fail - clients are optional
		} finally {
			safeSetState(() => _loadingClients = false);
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

	Future<void> _extractReminders(String noteId) async {
		_api.attachSession(_session);
		try {
			final resp = await _api.dio.post('/reminders/extract-from-note/$noteId');
			final createdReminders = resp.data as List;
			if (mounted) {
				ScaffoldMessenger.of(context).showSnackBar(
					SnackBar(
						content: Text(
							createdReminders.isEmpty
								? 'No reminders found in note'
								: 'Extracted ${createdReminders.length} reminder${createdReminders.length == 1 ? '' : 's'}',
						),
						action: createdReminders.isNotEmpty
							? SnackBarAction(
								label: 'View',
								onPressed: () {
									// Navigate to reminders tab and refresh
									final rootShell = context.findAncestorStateOfType<RootShellState>();
									rootShell?.navigateToReminders();
								},
							)
							: null,
					),
				);
			}
		} catch (e) {
			if (mounted) {
				ScaffoldMessenger.of(context).showSnackBar(
					SnackBar(content: Text('Failed to extract reminders: ${e.toString()}')),
				);
			}
		}
	}

	@override
	void initState() {
		super.initState();
		WidgetsBinding.instance.addPostFrameCallback((_) {
			_load();
			_loadClients();
		});
	}

	Widget _buildQuickActions() {
		final recentClients = _clients.take(5).toList();
		
		return Card(
			margin: const EdgeInsets.all(12),
			child: Column(
				crossAxisAlignment: CrossAxisAlignment.start,
				children: [
					Padding(
						padding: const EdgeInsets.all(16),
						child: Row(
							mainAxisAlignment: MainAxisAlignment.spaceBetween,
							children: [
								Text(
									'Quick Actions',
									style: Theme.of(context).textTheme.titleMedium?.copyWith(
										fontWeight: FontWeight.bold,
										color: AppColors.softCoral,
									),
								),
								TextButton.icon(
									onPressed: () async {
										await Navigator.of(context).push(
											MaterialPageRoute(builder: (_) => const ClientsScreen()),
										);
										_loadClients();
									},
									icon: const Icon(Icons.people, size: 18),
									label: const Text('All Clients'),
								),
							],
						),
					),
					if (_loadingClients)
						const Padding(
							padding: EdgeInsets.all(16),
							child: Center(child: CircularProgressIndicator()),
						)
					else if (recentClients.isEmpty)
						Padding(
							padding: const EdgeInsets.all(16),
							child: Row(
								children: [
									Icon(Icons.person_outline, size: 20, color: Colors.grey[600]),
									const SizedBox(width: 8),
									Text(
										'No clients yet',
										style: TextStyle(color: Colors.grey[600], fontSize: 14),
									),
								],
							),
						)
					else
						SizedBox(
							height: 80,
							child: ListView.builder(
								scrollDirection: Axis.horizontal,
								padding: const EdgeInsets.symmetric(horizontal: 8),
								itemCount: recentClients.length,
								itemBuilder: (context, index) {
									final client = recentClients[index] as Map<String, dynamic>;
									return Padding(
										padding: const EdgeInsets.symmetric(horizontal: 4),
										child: InkWell(
											onTap: () {
												// Could navigate to client detail or create note for client
											},
											child: Container(
												width: 120,
												padding: const EdgeInsets.all(12),
												decoration: BoxDecoration(
													border: Border.all(color: AppColors.softCoral.withOpacity(0.2)),
													borderRadius: BorderRadius.circular(12),
												),
												child: Column(
													mainAxisSize: MainAxisSize.min,
													crossAxisAlignment: CrossAxisAlignment.start,
													children: [
														Row(
															children: [
																Icon(Icons.person, size: 16, color: AppColors.softCoral),
																const SizedBox(width: 4),
																Expanded(
																	child: Text(
																		client['name'] ?? '',
																		style: const TextStyle(
																			fontSize: 12,
																			fontWeight: FontWeight.w600,
																		),
																		overflow: TextOverflow.ellipsis,
																	),
																),
															],
														),
														if (client['location'] != null && (client['location'] as String).isNotEmpty) ...[
															const SizedBox(height: 4),
															Text(
																client['location'] as String,
																style: TextStyle(
																	fontSize: 10,
																	color: Colors.grey[600],
																),
																overflow: TextOverflow.ellipsis,
															),
														],
													],
												),
											),
										),
									);
								},
							),
						),
					const SizedBox(height: 8),
				],
			),
		);
	}

	@override
	Widget build(BuildContext context) {
		return Scaffold(
			appBar: AppBar(title: const Text('Second Brain')),
			body: _loading
					? const Center(child: CircularProgressIndicator())
					: _error != null
							? Center(
								child: Padding(
									padding: const EdgeInsets.all(16),
									child: Column(
										mainAxisSize: MainAxisSize.min,
										children: [
											Icon(Icons.error_outline, size: 48, color: AppColors.deepRed),
											const SizedBox(height: 16),
											Text(
												_error!,
												style: TextStyle(color: AppColors.deepRed),
												textAlign: TextAlign.center,
											),
											const SizedBox(height: 16),
											FilledButton(
												onPressed: _load,
												child: const Text('Retry'),
											),
										],
									),
								),
							)
							: RefreshIndicator(
								onRefresh: () async {
									await _load();
									await _loadClients();
								},
								child: Column(
									children: [
										_buildQuickActions(),
										Expanded(
											child: _notes.isEmpty
												? Center(
													child: Column(
														mainAxisAlignment: MainAxisAlignment.center,
														children: [
															Icon(Icons.note_outlined, size: 64, color: Colors.grey[400]),
															const SizedBox(height: 16),
															Text(
																'No notes yet',
																style: TextStyle(color: Colors.grey[600], fontSize: 16),
															),
															const SizedBox(height: 8),
															Text(
																'Tap the mic button to record your first note',
																style: TextStyle(color: Colors.grey[500], fontSize: 12),
																textAlign: TextAlign.center,
															),
														],
													),
												)
												: ListView.separated(
													padding: const EdgeInsets.symmetric(horizontal: 12),
													itemBuilder: (context, i) {
										final n = _notes[i] as Map<String, dynamic>;
										final id = n['id'] as String;
										final status = (n['status'] as String?) ?? '';
										return Card(
											margin: const EdgeInsets.symmetric(horizontal: 0, vertical: 4),
											child: ListTile(
												title: Text(
													n['text'] ?? '(no text)',
													style: Theme.of(context).textTheme.bodyLarge,
												),
												subtitle: Row(
													children: [
														if (status == 'done')
															Container(
																padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
																decoration: BoxDecoration(
																	color: AppColors.emerald.withOpacity(0.1),
																	borderRadius: BorderRadius.circular(12),
																),
																child: Text(
																	'Done',
																	style: TextStyle(
																		color: AppColors.emerald,
																		fontSize: 12,
																		fontWeight: FontWeight.w600,
																	),
																),
															)
														else
															Text(
																'Status: $status',
																style: Theme.of(context).textTheme.bodySmall,
															),
													],
												),
												trailing: Wrap(spacing: 8, children: [
													IconButton(
														onPressed: () => _extractReminders(id),
														icon: const Icon(Icons.notifications_outlined),
														tooltip: 'Extract reminders',
														color: AppColors.warmAmber,
													),
													IconButton(
														onPressed: () => _shareNote(id),
														icon: const Icon(Icons.ios_share),
														tooltip: 'Share',
														color: AppColors.softCoral,
													),
													IconButton(
														onPressed: status == 'done' ? null : () => _markDone(id),
														icon: const Icon(Icons.check_circle_outline),
														tooltip: 'Mark done',
														color: status == 'done' ? AppColors.slateGrey : AppColors.emerald,
													),
												]),
											),
										);
													},
													separatorBuilder: (_, __) => const Divider(height: 1),
													itemCount: _notes.length,
												),
										),
									],
								),
						),
			floatingActionButton: FloatingActionButton.extended(
				onPressed: () async {
					await Navigator.of(context).push(
						MaterialPageRoute(builder: (_) => const VoiceCaptureScreen()),
					);
					if (mounted) {
						_load();
						_loadClients();
					}
				},
				label: const Text('Record Note'),
				icon: const Icon(Icons.mic),
			),
		);
	}
}
