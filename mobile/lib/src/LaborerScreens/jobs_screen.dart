import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';

import '../core/api_client.dart';
import '../core/session.dart';
import '../core/app_theme.dart';
import 'job_detail_screen.dart';

class JobsScreen extends StatefulWidget {
	const JobsScreen({super.key});

	@override
	State<JobsScreen> createState() => _JobsScreenState();
}

class _JobsScreenState extends State<JobsScreen> {
	List<dynamic> _jobs = [];
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
			final resJobs = await _api.dio.get('/jobs');
			if (!mounted) return;
			final resClients = await _api.dio.get('/clients');
			if (!mounted) return;
			safeSetState(() {
				_jobs = resJobs.data as List;
				_clients = resClients.data as List;
			});
		} on DioException catch (e) {
			safeSetState(() { _error = e.response?.data?.toString() ?? 'Failed to load'; });
		} finally {
			safeSetState(() { _loading = false; });
		}
	}

	Future<void> _createJob() async {
		String? selectedClientId;
		final siteCtrl = TextEditingController(text: '');
		final ok = await showDialog<bool>(
			context: context,
			builder: (_) => StatefulBuilder(
				builder: (context, setSt) => AlertDialog(
					title: const Text('New job'),
					content: Column(
						mainAxisSize: MainAxisSize.min,
						children: [
							DropdownButtonFormField<String>(
								items: _clients.map((c) => DropdownMenuItem<String>(value: c['id'] as String, child: Text(c['name'] as String))).toList(),
								value: selectedClientId,
								onChanged: (v) => setSt(() => selectedClientId = v),
								decoration: const InputDecoration(labelText: 'Client'),
							),
							TextField(controller: siteCtrl, decoration: const InputDecoration(labelText: 'Site')),
						],
					),
					actions: [
						TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
						FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Save')),
					],
				),
			),
		);
		if (ok != true || selectedClientId == null) return;
		try {
			await _api.dio.post('/jobs', data: {
				'client_id': selectedClientId,
				'site': siteCtrl.text.trim(),
				'status': 'open',
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
			appBar: AppBar(title: const Text('Jobs')),
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
								onRefresh: _load,
								child: ListView.separated(
									padding: const EdgeInsets.all(12),
									itemBuilder: (_, i) {
										final j = _jobs[i] as Map<String, dynamic>;
										final status = (j['status'] as String?) ?? '';
										return Card(
											margin: const EdgeInsets.symmetric(horizontal: 0, vertical: 4),
											child: ListTile(
												leading: CircleAvatar(
													backgroundColor: AppColors.warmAmber.withOpacity(0.1),
													child: Icon(Icons.work_outline, color: AppColors.warmAmber),
												),
												title: Text(
													j['site'] ?? '(no site)',
													style: Theme.of(context).textTheme.bodyLarge?.copyWith(
														fontWeight: FontWeight.w600,
													),
												),
												subtitle: Row(
													children: [
														Container(
															padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
															decoration: BoxDecoration(
																color: status == 'open'
																	? AppColors.warmAmber.withOpacity(0.1)
																	: AppColors.emerald.withOpacity(0.1),
																borderRadius: BorderRadius.circular(12),
															),
															child: Text(
																status,
																style: TextStyle(
																	color: status == 'open' ? AppColors.warmAmber : AppColors.emerald,
																	fontSize: 12,
																	fontWeight: FontWeight.w600,
																),
															),
														),
													],
												),
												onTap: () {
													Navigator.of(context).push(
														MaterialPageRoute(
															builder: (_) => JobDetailScreen(jobId: j['id'] as String),
														),
													);
												},
											),
										);
									},
									separatorBuilder: (_, __) => const Divider(height: 1),
									itemCount: _jobs.length,
							),
						),
			floatingActionButton: FloatingActionButton.extended(
				onPressed: _createJob,
				label: const Text('Add'),
				icon: const Icon(Icons.work_outline),
			),
		);
	}
}
