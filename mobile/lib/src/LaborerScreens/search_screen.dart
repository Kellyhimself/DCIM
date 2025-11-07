import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import 'package:intl/intl.dart';

import '../core/api_client.dart';
import '../core/session.dart';
import '../core/app_theme.dart';
import 'job_detail_screen.dart';

class SearchScreen extends StatefulWidget {
	const SearchScreen({super.key});

	@override
	State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
	final _qCtrl = TextEditingController();
	final _partCtrl = TextEditingController();
	final _phoneCtrl = TextEditingController();
	final _jobTypeCtrl = TextEditingController();
	final _locationCtrl = TextEditingController();
	
	List<dynamic> _clients = [];
	List<dynamic> _jobs = [];
	List<dynamic> _notes = [];
	bool _loading = false;
	String? _error;
	bool _showFilters = false;
	
	DateTime? _startDate;
	DateTime? _endDate;
	String? _jobStatus;

	ApiClient get _api => context.read<ApiClient>();
	Session get _session => context.read<Session>();

	Map<String, String?> _buildQueryParams() {
		final params = <String, String?>{};
		final q = _qCtrl.text.trim();
		if (q.isNotEmpty) params['q'] = q;
		if (_partCtrl.text.trim().isNotEmpty) params['part'] = _partCtrl.text.trim();
		if (_phoneCtrl.text.trim().isNotEmpty) params['phone'] = _phoneCtrl.text.trim();
		if (_jobTypeCtrl.text.trim().isNotEmpty) params['job_type'] = _jobTypeCtrl.text.trim();
		if (_locationCtrl.text.trim().isNotEmpty) params['location'] = _locationCtrl.text.trim();
		if (_startDate != null) params['start_date'] = DateFormat('yyyy-MM-dd').format(_startDate!);
		if (_endDate != null) params['end_date'] = DateFormat('yyyy-MM-dd').format(_endDate!);
		if (_jobStatus != null && _jobStatus!.isNotEmpty) params['status'] = _jobStatus;
		return params;
	}

	Future<void> _run() async {
		_api.attachSession(_session);
		setState(() { _loading = true; _error = null; });
		try {
			final params = _buildQueryParams();
			final res = await Future.wait([
				_api.dio.get('/search/clients', queryParameters: params),
				_api.dio.get('/search/jobs', queryParameters: params),
				_api.dio.get('/search/notes', queryParameters: params),
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

	void _clearFilters() {
		setState(() {
			_partCtrl.clear();
			_phoneCtrl.clear();
			_jobTypeCtrl.clear();
			_locationCtrl.clear();
			_startDate = null;
			_endDate = null;
			_jobStatus = null;
		});
	}

	bool get _hasActiveFilters {
		return _partCtrl.text.trim().isNotEmpty ||
			_phoneCtrl.text.trim().isNotEmpty ||
			_jobTypeCtrl.text.trim().isNotEmpty ||
			_locationCtrl.text.trim().isNotEmpty ||
			_startDate != null ||
			_endDate != null ||
			(_jobStatus != null && _jobStatus!.isNotEmpty);
	}

	Future<void> _selectDate(bool isStart) async {
		final picked = await showDatePicker(
			context: context,
			initialDate: isStart ? (_startDate ?? DateTime.now()) : (_endDate ?? DateTime.now()),
			firstDate: DateTime(2020),
			lastDate: DateTime.now(),
		);
		if (picked != null) {
			setState(() {
				if (isStart) {
					_startDate = picked;
				} else {
					_endDate = picked;
				}
			});
		}
	}

	@override
	Widget build(BuildContext context) {
		return Scaffold(
			appBar: AppBar(
				title: const Text('Search'),
				actions: [
					IconButton(
						icon: Icon(_showFilters ? Icons.filter_alt : Icons.filter_alt_outlined),
						onPressed: () => setState(() => _showFilters = !_showFilters),
						tooltip: 'Filters',
					),
				],
			),
			body: Column(
				children: [
					Flexible(
						child: SingleChildScrollView(
							child: Padding(
								padding: const EdgeInsets.all(12),
								child: Column(
									children: [
										Row(children: [
											Expanded(
												child: TextField(
													controller: _qCtrl,
													decoration: const InputDecoration(
														hintText: 'Search...',
														prefixIcon: Icon(Icons.search),
														isDense: true,
													),
													onSubmitted: (_) => _run(),
												),
											),
											const SizedBox(width: 8),
											FilledButton(
												onPressed: _loading ? null : _run,
												child: _loading
													? const SizedBox(
														width: 20,
														height: 20,
														child: CircularProgressIndicator(strokeWidth: 2),
													)
													: const Text('Search'),
											),
										]),
										if (_hasActiveFilters) ...[
											const SizedBox(height: 8),
											Wrap(
												spacing: 6,
												runSpacing: 6,
												children: [
													if (_partCtrl.text.trim().isNotEmpty)
														Chip(
															label: Text('Part: ${_partCtrl.text}'),
															onDeleted: () => setState(() => _partCtrl.clear()),
															deleteIcon: const Icon(Icons.close, size: 16),
														),
													if (_phoneCtrl.text.trim().isNotEmpty)
														Chip(
															label: Text('Phone: ${_phoneCtrl.text}'),
															onDeleted: () => setState(() => _phoneCtrl.clear()),
															deleteIcon: const Icon(Icons.close, size: 16),
														),
													if (_jobTypeCtrl.text.trim().isNotEmpty)
														Chip(
															label: Text('Type: ${_jobTypeCtrl.text}'),
															onDeleted: () => setState(() => _jobTypeCtrl.clear()),
															deleteIcon: const Icon(Icons.close, size: 16),
														),
													if (_locationCtrl.text.trim().isNotEmpty)
														Chip(
															label: Text('Location: ${_locationCtrl.text}'),
															onDeleted: () => setState(() => _locationCtrl.clear()),
															deleteIcon: const Icon(Icons.close, size: 16),
														),
													if (_startDate != null)
														Chip(
															label: Text('From: ${DateFormat('MMM d').format(_startDate!)}'),
															onDeleted: () => setState(() => _startDate = null),
															deleteIcon: const Icon(Icons.close, size: 16),
														),
													if (_endDate != null)
														Chip(
															label: Text('To: ${DateFormat('MMM d').format(_endDate!)}'),
															onDeleted: () => setState(() => _endDate = null),
															deleteIcon: const Icon(Icons.close, size: 16),
														),
													if (_jobStatus != null && _jobStatus!.isNotEmpty)
														Chip(
															label: Text('Status: $_jobStatus'),
															onDeleted: () => setState(() => _jobStatus = null),
															deleteIcon: const Icon(Icons.close, size: 16),
														),
													TextButton.icon(
														onPressed: _clearFilters,
														icon: const Icon(Icons.clear_all, size: 16),
														label: const Text('Clear all'),
														style: TextButton.styleFrom(
															padding: const EdgeInsets.symmetric(horizontal: 8),
															minimumSize: const Size(0, 32),
														),
													),
												],
											),
										],
										if (_showFilters) ...[
											const SizedBox(height: 12),
											Card(
												child: Padding(
													padding: const EdgeInsets.all(12),
													child: Column(
														crossAxisAlignment: CrossAxisAlignment.start,
														children: [
															Row(
																mainAxisAlignment: MainAxisAlignment.spaceBetween,
																children: [
																	Text(
																		'Filters',
																		style: Theme.of(context).textTheme.titleSmall?.copyWith(
																			fontWeight: FontWeight.bold,
																		),
																	),
																	if (_hasActiveFilters)
																		TextButton(
																			onPressed: _clearFilters,
																			child: const Text('Clear', style: TextStyle(fontSize: 12)),
																		),
																],
															),
															const SizedBox(height: 12),
															TextFormField(
																controller: _partCtrl,
																decoration: const InputDecoration(
																	labelText: 'Part name',
																	hintText: 'e.g., P-trap, MCB',
																	isDense: true,
																	prefixIcon: Icon(Icons.build, size: 20),
																),
															),
															const SizedBox(height: 8),
															TextFormField(
																controller: _phoneCtrl,
																decoration: const InputDecoration(
																	labelText: 'Phone number',
																	hintText: 'e.g., 0712345678',
																	isDense: true,
																	prefixIcon: Icon(Icons.phone, size: 20),
																),
																keyboardType: TextInputType.phone,
															),
															const SizedBox(height: 8),
															TextFormField(
																controller: _jobTypeCtrl,
																decoration: const InputDecoration(
																	labelText: 'Job type',
																	hintText: 'e.g., plumbing, electrical',
																	isDense: true,
																	prefixIcon: Icon(Icons.work_outline, size: 20),
																),
															),
															const SizedBox(height: 8),
															TextFormField(
																controller: _locationCtrl,
																decoration: const InputDecoration(
																	labelText: 'Location',
																	hintText: 'e.g., Parklands, Karen',
																	isDense: true,
																	prefixIcon: Icon(Icons.location_on, size: 20),
																),
															),
															const SizedBox(height: 8),
															Row(
																children: [
																	Expanded(
																		child: OutlinedButton.icon(
																			onPressed: () => _selectDate(true),
																			icon: const Icon(Icons.calendar_today, size: 16),
																			label: Text(
																				_startDate == null
																					? 'Start date'
																					: DateFormat('MMM d, y').format(_startDate!),
																				style: const TextStyle(fontSize: 12),
																			),
																		),
																	),
																	const SizedBox(width: 8),
																	Expanded(
																		child: OutlinedButton.icon(
																			onPressed: () => _selectDate(false),
																			icon: const Icon(Icons.calendar_today, size: 16),
																			label: Text(
																				_endDate == null
																					? 'End date'
																					: DateFormat('MMM d, y').format(_endDate!),
																				style: const TextStyle(fontSize: 12),
																			),
																		),
																	),
																],
															),
															const SizedBox(height: 8),
															DropdownButtonFormField<String>(
																value: _jobStatus,
																decoration: const InputDecoration(
																	labelText: 'Job status',
																	isDense: true,
																	prefixIcon: Icon(Icons.info_outline, size: 20),
																),
																items: const [
																	DropdownMenuItem(value: 'open', child: Text('Open')),
																	DropdownMenuItem(value: 'closed', child: Text('Closed')),
																],
																onChanged: (v) => setState(() => _jobStatus = v),
															),
														],
													),
												),
											),
										],
									],
								),
							),
						),
					),
					if (_error != null)
						Padding(
							padding: const EdgeInsets.symmetric(horizontal: 12),
							child: Container(
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
												style: TextStyle(color: AppColors.deepRed, fontSize: 12),
											),
										),
									],
								),
							),
						),
					Expanded(
						child: _loading
							? const Center(child: CircularProgressIndicator())
							: RefreshIndicator(
								onRefresh: _run,
								child: ListView(
									padding: const EdgeInsets.symmetric(horizontal: 12),
									children: [
										if (_clients.isNotEmpty) ...[
											Padding(
												padding: const EdgeInsets.symmetric(vertical: 8),
												child: Row(
													children: [
														Icon(Icons.person, size: 18, color: AppColors.deepTeal),
														const SizedBox(width: 8),
														Text(
															'Clients (${_clients.length})',
															style: Theme.of(context).textTheme.titleSmall?.copyWith(
																fontWeight: FontWeight.bold,
																color: AppColors.deepTeal,
															),
														),
													],
												),
											),
											..._clients.map((c) => Card(
												margin: const EdgeInsets.only(bottom: 6),
												child: ListTile(
													dense: true,
													leading: CircleAvatar(
														radius: 18,
														backgroundColor: AppColors.deepTeal.withOpacity(0.1),
														child: Icon(Icons.person, color: AppColors.deepTeal, size: 18),
													),
													title: Text(
														c['name'] ?? '',
														style: const TextStyle(fontSize: 14),
													),
													subtitle: Text(
														(c['phone'] ?? '') as String,
														style: const TextStyle(fontSize: 12),
													),
												),
											)).toList(),
										],
										if (_jobs.isNotEmpty) ...[
											const SizedBox(height: 8),
											Padding(
												padding: const EdgeInsets.symmetric(vertical: 8),
												child: Row(
													children: [
														Icon(Icons.work_outline, size: 18, color: AppColors.warmAmber),
														const SizedBox(width: 8),
														Text(
															'Jobs (${_jobs.length})',
															style: Theme.of(context).textTheme.titleSmall?.copyWith(
																fontWeight: FontWeight.bold,
																color: AppColors.warmAmber,
															),
														),
													],
												),
											),
											..._jobs.map((j) => Card(
												margin: const EdgeInsets.only(bottom: 6),
												child: ListTile(
													dense: true,
													leading: CircleAvatar(
														radius: 18,
														backgroundColor: AppColors.warmAmber.withOpacity(0.1),
														child: Icon(Icons.work_outline, color: AppColors.warmAmber, size: 18),
													),
													title: Text(
														j['site'] ?? '',
														style: const TextStyle(fontSize: 14),
													),
													subtitle: Text(
														'Status: ${j['status']}',
														style: const TextStyle(fontSize: 12),
													),
													onTap: () {
														Navigator.push(
															context,
															MaterialPageRoute(
																builder: (_) => JobDetailScreen(jobId: j['id']),
															),
														);
													},
												),
											)).toList(),
										],
										if (_notes.isNotEmpty) ...[
											const SizedBox(height: 8),
											Padding(
												padding: const EdgeInsets.symmetric(vertical: 8),
												child: Row(
													children: [
														Icon(Icons.note, size: 18, color: AppColors.softCoral),
														const SizedBox(width: 8),
														Text(
															'Notes (${_notes.length})',
															style: Theme.of(context).textTheme.titleSmall?.copyWith(
																fontWeight: FontWeight.bold,
																color: AppColors.softCoral,
															),
														),
													],
												),
											),
											..._notes.map((n) => Card(
												margin: const EdgeInsets.only(bottom: 6),
												child: ListTile(
													dense: true,
													leading: CircleAvatar(
														radius: 18,
														backgroundColor: AppColors.softCoral.withOpacity(0.1),
														child: Icon(Icons.note, color: AppColors.softCoral, size: 18),
													),
													title: Text(
														(n['text'] ?? '').length > 60
															? '${(n['text'] ?? '').substring(0, 60)}...'
															: (n['text'] ?? ''),
														style: const TextStyle(fontSize: 14),
														maxLines: 2,
														overflow: TextOverflow.ellipsis,
													),
													subtitle: Text(
														'Status: ${n['status']}',
														style: const TextStyle(fontSize: 12),
													),
												),
											)).toList(),
										],
										if (_clients.isEmpty && _jobs.isEmpty && _notes.isEmpty && !_loading)
											Center(
												child: Padding(
													padding: const EdgeInsets.all(32),
													child: Column(
														mainAxisSize: MainAxisSize.min,
														children: [
															Icon(Icons.search_off, size: 64, color: AppColors.slateGrey),
															const SizedBox(height: 16),
															Text(
																'No results found',
																style: Theme.of(context).textTheme.bodyLarge?.copyWith(
																	color: AppColors.slateGrey,
																),
															),
															const SizedBox(height: 8),
															Text(
																'Try adjusting your search or filters',
																style: Theme.of(context).textTheme.bodySmall?.copyWith(
																	color: AppColors.slateGrey,
																),
															),
														],
													),
												),
											),
									],
								),
							),
					),
				],
			),
		);
	}
}
