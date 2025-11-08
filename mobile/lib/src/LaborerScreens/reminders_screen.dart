import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import 'package:intl/intl.dart';

import '../core/api_client.dart';
import '../core/session.dart';

class RemindersScreen extends StatefulWidget {
	const RemindersScreen({super.key});

	@override
	State<RemindersScreen> createState() => RemindersScreenState();
}

class RemindersScreenState extends State<RemindersScreen> with WidgetsBindingObserver {
	List<dynamic> _reminders = [];
	bool _loading = true;
	String? _error;
	String? _filterStatus; // pending, completed, cancelled
	String? _filterType; // follow_up, call, return, etc.

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
			final params = <String, String?>{};
			if (_filterStatus != null) params['status'] = _filterStatus;
			if (_filterType != null) params['type'] = _filterType;
			
			final resp = await _api.dio.get('/reminders', queryParameters: params);
			if (!mounted) return;
			safeSetState(() {
				_reminders = resp.data as List;
			});
		} on DioException catch (e) {
			safeSetState(() { _error = e.response?.data?.toString() ?? 'Failed to load reminders'; });
		} finally {
			safeSetState(() { _loading = false; });
		}
	}

	Future<void> _updateStatus(String reminderId, String status) async {
		try {
			await _api.dio.put('/reminders/$reminderId', data: {'status': status});
			await _load();
		} on DioException catch (e) {
			if (mounted) {
				ScaffoldMessenger.of(context).showSnackBar(
					SnackBar(content: Text(e.response?.data?.toString() ?? 'Failed to update reminder')),
				);
			}
		}
	}

	Future<void> _deleteReminder(String reminderId) async {
		final confirmed = await showDialog<bool>(
			context: context,
			builder: (context) => AlertDialog(
				title: const Text('Delete Reminder'),
				content: const Text('Are you sure you want to delete this reminder?'),
				actions: [
					TextButton(
						onPressed: () => Navigator.pop(context, false),
						child: const Text('Cancel'),
					),
					TextButton(
						onPressed: () => Navigator.pop(context, true),
						child: const Text('Delete', style: TextStyle(color: Colors.red)),
					),
				],
			),
		);
		
		if (confirmed != true) return;
		
		try {
			await _api.dio.delete('/reminders/$reminderId');
			await _load();
			if (mounted) {
				ScaffoldMessenger.of(context).showSnackBar(
					const SnackBar(content: Text('Reminder deleted')),
				);
			}
		} on DioException catch (e) {
			if (mounted) {
				ScaffoldMessenger.of(context).showSnackBar(
					SnackBar(content: Text(e.response?.data?.toString() ?? 'Failed to delete reminder')),
				);
			}
		}
	}


	@override
	void initState() {
		super.initState();
		WidgetsBinding.instance.addObserver(this);
		WidgetsBinding.instance.addPostFrameCallback((_) => _load());
	}

	@override
	void dispose() {
		WidgetsBinding.instance.removeObserver(this);
		super.dispose();
	}

	@override
	void didChangeAppLifecycleState(AppLifecycleState state) {
		if (state == AppLifecycleState.resumed) {
			// Refresh when app comes to foreground
			_load();
		}
	}

	// Public method to refresh reminders (can be called from other screens)
	void refreshReminders() {
		_load();
	}

	Widget _buildFilterChips() {
		return Wrap(
			spacing: 8,
			children: [
				FilterChip(
					label: const Text('All'),
					selected: _filterStatus == null,
					onSelected: (selected) {
						if (selected) {
							setState(() => _filterStatus = null);
							_load();
						}
					},
				),
				FilterChip(
					label: const Text('Pending'),
					selected: _filterStatus == 'pending',
					onSelected: (selected) {
						setState(() => _filterStatus = selected ? 'pending' : null);
						_load();
					},
				),
				FilterChip(
					label: const Text('Completed'),
					selected: _filterStatus == 'completed',
					onSelected: (selected) {
						setState(() => _filterStatus = selected ? 'completed' : null);
						_load();
					},
				),
			],
		);
	}

	Widget _buildReminderCard(dynamic reminder) {
		final status = reminder['status'] as String? ?? 'pending';
		final type = reminder['type'] as String? ?? 'follow_up';
		final text = reminder['text'] as String? ?? '';
		final dueDateText = reminder['due_date_text'] as String?;
		final dueDate = reminder['due_date'] as String?;
		final completedAt = reminder['completed_at'] as String?;
		
		DateTime? parsedDueDate;
		if (dueDate != null) {
			try {
				parsedDueDate = DateTime.parse(dueDate);
			} catch (_) {}
		}
		
		final isOverdue = parsedDueDate != null && 
			parsedDueDate.isBefore(DateTime.now()) && 
			status == 'pending';
		
		IconData typeIcon;
		Color typeColor;
		switch (type) {
			case 'call':
				typeIcon = Icons.phone;
				typeColor = Colors.blue;
				break;
			case 'return':
			case 'follow_up':
				typeIcon = Icons.arrow_back;
				typeColor = Colors.orange;
				break;
			case 'check':
				typeIcon = Icons.check_circle_outline;
				typeColor = Colors.green;
				break;
			case 'meeting':
				typeIcon = Icons.event;
				typeColor = Colors.purple;
				break;
			default:
				typeIcon = Icons.notifications_outlined;
				typeColor = Colors.grey;
		}
		
		return Card(
			margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
			child: ListTile(
				leading: CircleAvatar(
					backgroundColor: typeColor.withOpacity(0.2),
					child: Icon(typeIcon, color: typeColor, size: 20),
				),
				title: Text(
					text,
					style: TextStyle(
						decoration: status == 'completed' ? TextDecoration.lineThrough : null,
						color: status == 'completed' ? Colors.grey : null,
					),
				),
				subtitle: Column(
					crossAxisAlignment: CrossAxisAlignment.start,
					children: [
						if (dueDateText != null || parsedDueDate != null)
							Text(
								dueDateText ?? DateFormat('MMM d, y').format(parsedDueDate!),
								style: TextStyle(
									color: isOverdue ? Colors.red : Colors.grey[600],
									fontWeight: isOverdue ? FontWeight.bold : null,
								),
							),
						if (completedAt != null)
							Text(
								'Completed ${DateFormat('MMM d, y').format(DateTime.parse(completedAt))}',
								style: TextStyle(color: Colors.green[600], fontSize: 12),
							),
					],
				),
				trailing: PopupMenuButton(
					itemBuilder: (context) => [
						if (status == 'pending')
							PopupMenuItem(
								child: const Row(
									children: [
										Icon(Icons.check, color: Colors.green),
										SizedBox(width: 8),
										Text('Mark Complete'),
									],
								),
								onTap: () => _updateStatus(reminder['id'] as String, 'completed'),
							),
						if (status == 'completed')
							PopupMenuItem(
								child: const Row(
									children: [
										Icon(Icons.undo, color: Colors.orange),
										SizedBox(width: 8),
										Text('Mark Pending'),
									],
								),
								onTap: () => _updateStatus(reminder['id'] as String, 'pending'),
							),
						PopupMenuItem(
							child: const Row(
								children: [
									Icon(Icons.delete, color: Colors.red),
									SizedBox(width: 8),
									Text('Delete'),
								],
							),
							onTap: () => _deleteReminder(reminder['id'] as String),
						),
					],
				),
			),
		);
	}

	@override
	Widget build(BuildContext context) {
		return Scaffold(
			appBar: AppBar(
				title: const Text('Reminders'),
				actions: [
					IconButton(
						icon: const Icon(Icons.refresh),
						onPressed: _load,
						tooltip: 'Refresh',
					),
				],
			),
			body: _loading
				? const Center(child: CircularProgressIndicator())
				: _error != null
					? Center(
						child: Column(
							mainAxisAlignment: MainAxisAlignment.center,
							children: [
								Text(_error!, style: const TextStyle(color: Colors.red)),
								const SizedBox(height: 16),
								ElevatedButton(
									onPressed: _load,
									child: const Text('Retry'),
								),
							],
						),
					)
					: RefreshIndicator(
						onRefresh: _load,
						child: Column(
							children: [
								Padding(
									padding: const EdgeInsets.all(16),
									child: _buildFilterChips(),
								),
								Expanded(
									child: _reminders.isEmpty
										? Center(
											child: Column(
												mainAxisAlignment: MainAxisAlignment.center,
												children: [
													Icon(Icons.notifications_none, size: 64, color: Colors.grey[400]),
													const SizedBox(height: 16),
													Text(
														'No reminders',
														style: TextStyle(color: Colors.grey[600], fontSize: 16),
													),
													const SizedBox(height: 8),
													Text(
														'Reminders will appear here when extracted from notes',
														style: TextStyle(color: Colors.grey[500], fontSize: 12),
														textAlign: TextAlign.center,
													),
												],
											),
										)
										: ListView.builder(
											itemCount: _reminders.length,
											itemBuilder: (context, index) => _buildReminderCard(_reminders[index]),
										),
								),
							],
						),
					),
		);
	}
}

