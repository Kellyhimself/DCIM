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
import 'accounts_screen.dart';

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
			appBar: AppBar(
				title: const Text('Second Brain'),
				actions: [
					IconButton(
						icon: const Icon(Icons.account_circle_outlined),
						onPressed: () {
							Navigator.of(context).push(
								MaterialPageRoute(builder: (_) => const AccountsScreen()),
							);
						},
						tooltip: 'Account Settings',
					),
				],
			),
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
										final noteText = n['text'] ?? '(no text)';
										return _NoteCard(
											noteId: id,
											noteText: noteText,
											status: status,
											onExtractReminders: () => _extractReminders(id),
											onShare: () => _shareNote(id),
											onMarkDone: status == 'done' ? null : () => _markDone(id),
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

class _NoteCard extends StatefulWidget {
	final String noteId;
	final String noteText;
	final String status;
	final VoidCallback onExtractReminders;
	final VoidCallback onShare;
	final VoidCallback? onMarkDone;

	const _NoteCard({
		required this.noteId,
		required this.noteText,
		required this.status,
		required this.onExtractReminders,
		required this.onShare,
		this.onMarkDone,
	});

	@override
	State<_NoteCard> createState() => _NoteCardState();
}

class _NoteCardState extends State<_NoteCard> {
	bool _expanded = false;

	@override
	Widget build(BuildContext context) {
		final isLongText = widget.noteText.length > 100;
		final displayText = _expanded || !isLongText
			? widget.noteText
			: '${widget.noteText.substring(0, 100)}...';

		return Card(
			margin: const EdgeInsets.symmetric(horizontal: 0, vertical: 4),
			child: Column(
				crossAxisAlignment: CrossAxisAlignment.start,
				children: [
					Padding(
						padding: const EdgeInsets.all(12),
						child: Column(
							crossAxisAlignment: CrossAxisAlignment.start,
							children: [
								Row(
									children: [
										if (widget.status == 'done')
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
										else if (widget.status.isNotEmpty)
											Container(
												padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
												decoration: BoxDecoration(
													color: AppColors.warmAmber.withOpacity(0.1),
													borderRadius: BorderRadius.circular(12),
												),
												child: Text(
													widget.status,
													style: TextStyle(
														color: AppColors.warmAmber,
														fontSize: 12,
														fontWeight: FontWeight.w600,
													),
												),
											),
										const Spacer(),
										if (isLongText)
											TextButton(
												onPressed: () {
													setState(() => _expanded = !_expanded);
												},
												child: Text(
													_expanded ? 'Show less' : 'Show more',
													style: TextStyle(fontSize: 12),
												),
											),
									],
								),
								const SizedBox(height: 8),
								Text(
									displayText,
									style: Theme.of(context).textTheme.bodyMedium,
								),
							],
						),
					),
					Divider(height: 1),
					Padding(
						padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
						child: Row(
							children: [
								Expanded(
									child: TextButton.icon(
										onPressed: widget.onExtractReminders,
										icon: const Icon(Icons.notifications_outlined, size: 18),
										label: const Text('Reminders'),
										style: TextButton.styleFrom(
											foregroundColor: AppColors.warmAmber,
										),
									),
								),
								Expanded(
									child: TextButton.icon(
										onPressed: widget.onShare,
										icon: const Icon(Icons.ios_share, size: 18),
										label: const Text('Share'),
										style: TextButton.styleFrom(
											foregroundColor: AppColors.softCoral,
										),
									),
								),
								Expanded(
									child: TextButton.icon(
										onPressed: widget.onMarkDone,
										icon: Icon(
											widget.status == 'done' ? Icons.check_circle : Icons.check_circle_outline,
											size: 18,
										),
										label: Text(widget.status == 'done' ? 'Done' : 'Mark Done'),
										style: TextButton.styleFrom(
											foregroundColor: widget.status == 'done' ? AppColors.slateGrey : AppColors.emerald,
										),
									),
								),
							],
						),
					),
				],
			),
		);
	}
}
