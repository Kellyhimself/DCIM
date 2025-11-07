import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import 'package:share_plus/share_plus.dart';
import 'package:cross_file/cross_file.dart';
import 'package:intl/intl.dart';
import 'package:path_provider/path_provider.dart';

import '../core/api_client.dart';
import '../core/session.dart';
import '../core/app_theme.dart';
import 'voice_capture_screen.dart';

class JobDetailScreen extends StatefulWidget {
	final String jobId;
	
	const JobDetailScreen({super.key, required this.jobId});

	@override
	State<JobDetailScreen> createState() => _JobDetailScreenState();
}

class _JobDetailScreenState extends State<JobDetailScreen> {
	Map<String, dynamic>? _job;
	Map<String, dynamic>? _client;
	List<dynamic> _notes = [];
	Map<String, dynamic>? _entities;
	bool _loading = true;
	bool _generatingPdf = false;
	bool _updatingStatus = false;
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
			// Fetch job details
			final jobResp = await _api.dio.get('/jobs/${widget.jobId}');
			if (!mounted) return;
			final job = jobResp.data as Map<String, dynamic>;
			
			// Fetch client details
			Map<String, dynamic>? client;
			if (job['client_id'] != null) {
				try {
					final clientsResp = await _api.dio.get('/clients');
					if (mounted) {
						final clients = clientsResp.data as List;
						client = clients.firstWhere(
							(c) => c['id'] == job['client_id'],
							orElse: () => null,
						) as Map<String, dynamic>?;
					}
				} catch (e) {
					print('Error fetching client: $e');
				}
			}
			
			// Fetch all notes and filter by job_id
			final notesResp = await _api.dio.get('/notes');
			if (!mounted) return;
			final allNotes = notesResp.data as List;
			final jobNotes = allNotes.where((n) => n['job_id'] == job['id']).toList();
			
			// Extract entities from all notes combined
			Map<String, dynamic>? entities;
			if (jobNotes.isNotEmpty) {
				final allText = jobNotes
					.where((n) => n['text'] != null && (n['text'] as String).isNotEmpty)
					.map((n) => n['text'] as String)
					.join(' ');
				
				if (allText.isNotEmpty) {
					try {
						final nlpResp = await _api.dio.post('/nlp/tag', data: {
							'text': allText,
							'region': 'KE',
						});
						if (mounted) {
							entities = nlpResp.data as Map<String, dynamic>;
						}
					} catch (e) {
						print('Error extracting entities: $e');
					}
				}
			}
			
			safeSetState(() {
				_job = job;
				_client = client;
				_notes = jobNotes;
				_entities = entities;
			});
		} on DioException catch (e) {
			safeSetState(() {
				_error = e.response?.data?.toString() ?? 'Failed to load job details';
			});
		} finally {
			safeSetState(() => _loading = false);
		}
	}

	Future<void> _updateJobStatus(String newStatus) async {
		if (_job == null) return;
		
		safeSetState(() => _updatingStatus = true);
		_api.attachSession(_session);
		try {
			await _api.dio.put('/jobs/${widget.jobId}', data: {
				'client_id': _job!['client_id'],
				'site': _job!['site'],
				'status': newStatus,
			});
			await _load();
		} catch (e) {
			if (!mounted) return;
			ScaffoldMessenger.of(context).showSnackBar(
				SnackBar(
					content: Text('Failed to update status: ${e.toString()}'),
					backgroundColor: AppColors.deepRed,
					duration: const Duration(seconds: 2),
				),
			);
		} finally {
			safeSetState(() => _updatingStatus = false);
		}
	}

	Future<void> _createNote() async {
		await Navigator.of(context).push(
			MaterialPageRoute(
				builder: (_) => const VoiceCaptureScreen(),
			),
		);
		// Reload to show any new notes
		if (mounted) {
			await _load();
		}
	}

	Future<void> _generatePdf() async {
		if (_job == null) return;
		
		safeSetState(() => _generatingPdf = true);
		_api.attachSession(_session);
		try {
			// Generate PDF
			print('Generating PDF for job ${widget.jobId}...');
			final resp = await _api.dio.post('/jobs/${widget.jobId}/pdf');
			final pdfUrl = resp.data['url'] as String;
			print('PDF generated, downloading from: $pdfUrl');
			
			if (!mounted) return;
			
			// Download PDF to temp file using API client (with auth)
			final tempDir = await getTemporaryDirectory();
			final fileName = 'job-card-${widget.jobId}.pdf';
			final filePath = '${tempDir.path}/$fileName';
			print('Downloading PDF to: $filePath');
			
			// Use API client's Dio instance which has authentication and proper base URL
			await _api.dio.download(
				pdfUrl, // This is a relative URL like "/jobs/{id}/pdf/download"
				filePath,
				options: Options(
					receiveTimeout: const Duration(seconds: 60), // Longer for file downloads
				),
				onReceiveProgress: (received, total) {
					if (total != -1) {
						final progress = (received / total * 100).toStringAsFixed(0);
						print('Download progress: $progress%');
					}
				},
			);
			
			print('PDF downloaded successfully');
			
			// Verify file exists
			final file = File(filePath);
			if (!await file.exists()) {
				throw Exception('Downloaded file not found');
			}
			
			final fileSize = await file.length();
			print('PDF file size: $fileSize bytes');
			
			if (!mounted) return;
			
			// Share the PDF file
			print('Sharing PDF...');
			await Share.shareXFiles(
				[XFile(filePath)],
				subject: 'Job Card - ${_job!['site'] ?? 'Job'}',
				text: 'Job Card for ${_job!['site'] ?? 'Job'}',
			);
			print('PDF shared successfully');
			
			if (!mounted) return;
			ScaffoldMessenger.of(context).showSnackBar(
				const SnackBar(
					content: Text('PDF generated and ready to share'),
					backgroundColor: AppColors.emerald,
					duration: Duration(seconds: 2),
				),
			);
		} on DioException catch (e) {
			print('DioException during PDF generation: ${e.type} - ${e.message}');
			if (!mounted) return;
			String errorMsg = 'Failed to generate PDF';
			if (e.type == DioExceptionType.connectionTimeout || e.type == DioExceptionType.receiveTimeout) {
				errorMsg = 'PDF download timed out. Please try again.';
			} else if (e.type == DioExceptionType.connectionError) {
				errorMsg = 'Cannot connect to server. Check your connection.';
			} else {
				errorMsg = 'Failed: ${e.response?.data?.toString() ?? e.message ?? 'Unknown error'}';
			}
			ScaffoldMessenger.of(context).showSnackBar(
				SnackBar(
					content: Text(errorMsg),
					backgroundColor: AppColors.deepRed,
					duration: const Duration(seconds: 4),
				),
			);
		} catch (e, stackTrace) {
			print('Error during PDF generation: $e');
			print('Stack trace: $stackTrace');
			if (!mounted) return;
			ScaffoldMessenger.of(context).showSnackBar(
				SnackBar(
					content: Text('Failed to share PDF: ${e.toString()}'),
					backgroundColor: AppColors.deepRed,
					duration: const Duration(seconds: 4),
				),
			);
		} finally {
			safeSetState(() => _generatingPdf = false);
		}
	}

	@override
	void initState() {
		super.initState();
		WidgetsBinding.instance.addPostFrameCallback((_) => _load());
	}

	@override
	Widget build(BuildContext context) {
		return Scaffold(
			appBar: AppBar(
				title: Text(_job?['site'] ?? 'Job Details'),
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
						onRefresh: _load,
						child: SingleChildScrollView(
							padding: const EdgeInsets.all(12),
							child: Column(
								crossAxisAlignment: CrossAxisAlignment.start,
								children: [
									// Job Info Card - Compact
									Card(
										child: Padding(
											padding: const EdgeInsets.all(12),
											child: Column(
												crossAxisAlignment: CrossAxisAlignment.start,
												children: [
													Row(
														children: [
															Expanded(
																child: Text(
																	_job?['site'] ?? '(no site)',
																	style: Theme.of(context).textTheme.titleMedium?.copyWith(
																		fontWeight: FontWeight.bold,
																	),
																),
															),
															// Status Toggle - Compact
															GestureDetector(
																onTap: _updatingStatus ? null : () {
																	final currentStatus = _job?['status'] ?? 'open';
																	_updateJobStatus(currentStatus == 'open' ? 'closed' : 'open');
																},
																child: Container(
																	padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
																	decoration: BoxDecoration(
																		color: (_job?['status'] == 'open' ? AppColors.warmAmber : AppColors.emerald).withOpacity(0.1),
																		borderRadius: BorderRadius.circular(12),
																	),
																	child: Row(
																		mainAxisSize: MainAxisSize.min,
																		children: [
																			if (_updatingStatus)
																				const SizedBox(
																					width: 12,
																					height: 12,
																					child: CircularProgressIndicator(strokeWidth: 2),
																				)
																			else
																				Icon(
																					_job?['status'] == 'open' ? Icons.radio_button_unchecked : Icons.check_circle,
																					size: 14,
																					color: _job?['status'] == 'open' ? AppColors.warmAmber : AppColors.emerald,
																				),
																			const SizedBox(width: 4),
																			Text(
																				_job?['status'] ?? 'unknown',
																				style: TextStyle(
																					color: _job?['status'] == 'open' ? AppColors.warmAmber : AppColors.emerald,
																					fontWeight: FontWeight.w600,
																					fontSize: 11,
																				),
																			),
																		],
																	),
																),
															),
														],
													),
													if (_client != null) ...[
														const SizedBox(height: 8),
														Row(
															children: [
																Icon(Icons.person_outline, size: 16, color: AppColors.deepTeal),
																const SizedBox(width: 6),
																Expanded(
																	child: Text(
																		_client!['name'] ?? '',
																		style: Theme.of(context).textTheme.bodySmall?.copyWith(
																			fontWeight: FontWeight.w600,
																		),
																	),
																),
																if (_client!['phone'] != null)
																	Text(
																		_client!['phone'],
																		style: Theme.of(context).textTheme.bodySmall?.copyWith(
																			color: AppColors.slateGrey,
																			fontSize: 11,
																		),
																	),
															],
														),
													],
												],
											),
										),
									),
									
									const SizedBox(height: 8),
									
									// Action Buttons Row - Compact
									Row(
										children: [
											Expanded(
												child: OutlinedButton.icon(
													onPressed: _createNote,
													icon: const Icon(Icons.add, size: 18),
													label: const Text('Add Note', style: TextStyle(fontSize: 13)),
													style: OutlinedButton.styleFrom(
														foregroundColor: AppColors.deepTeal,
														side: BorderSide(color: AppColors.deepTeal),
														padding: const EdgeInsets.symmetric(vertical: 10),
													),
												),
											),
											const SizedBox(width: 8),
											Expanded(
												child: FilledButton.icon(
													onPressed: _generatingPdf ? null : _generatePdf,
													icon: _generatingPdf
														? const SizedBox(
															width: 16,
															height: 16,
															child: CircularProgressIndicator(strokeWidth: 2),
															)
														: const Icon(Icons.picture_as_pdf, size: 18),
													label: Text(
														_generatingPdf ? 'Generating...' : 'PDF',
														style: const TextStyle(fontSize: 13),
													),
													style: FilledButton.styleFrom(
														backgroundColor: AppColors.deepTeal,
														foregroundColor: Colors.white,
														padding: const EdgeInsets.symmetric(vertical: 10),
													),
												),
											),
										],
									),
									
									// Entities Summary - Compact (only if entities exist)
									if (_entities != null && _hasEntities(_entities!)) ...[
										const SizedBox(height: 12),
										Card(
											color: AppColors.deepTeal.withOpacity(0.05),
											child: Padding(
												padding: const EdgeInsets.all(10),
												child: Wrap(
													spacing: 6,
													runSpacing: 6,
													children: [
														if (_entities!['parts'] != null && (_entities!['parts'] as List).isNotEmpty)
															...(_entities!['parts'] as List).take(3).map((p) => Chip(
																label: Text(p.toString(), style: const TextStyle(fontSize: 11)),
																avatar: const Icon(Icons.build, size: 14),
																padding: EdgeInsets.zero,
																labelPadding: const EdgeInsets.symmetric(horizontal: 6),
																materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
																visualDensity: VisualDensity.compact,
															)),
														if (_entities!['amounts'] != null && (_entities!['amounts'] as List).isNotEmpty)
															...(_entities!['amounts'] as List).take(2).map((a) => Chip(
																label: Text(a.toString(), style: const TextStyle(fontSize: 11)),
																avatar: const Icon(Icons.attach_money, size: 14),
																padding: EdgeInsets.zero,
																labelPadding: const EdgeInsets.symmetric(horizontal: 6),
																materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
																visualDensity: VisualDensity.compact,
															)),
														if (_entities!['dates'] != null && (_entities!['dates'] as List).isNotEmpty)
															...(_entities!['dates'] as List).take(2).map((d) => Chip(
																label: Text(d.toString(), style: const TextStyle(fontSize: 11)),
																avatar: const Icon(Icons.calendar_today, size: 14),
																padding: EdgeInsets.zero,
																labelPadding: const EdgeInsets.symmetric(horizontal: 6),
																materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
																visualDensity: VisualDensity.compact,
															)),
													],
												),
											),
										),
									],
									
									const SizedBox(height: 12),
									
									// Notes Section Header - Compact
									Row(
										children: [
											Text(
												'Notes',
												style: Theme.of(context).textTheme.titleSmall?.copyWith(
													fontWeight: FontWeight.bold,
													color: AppColors.deepTeal,
												),
											),
											const SizedBox(width: 6),
											Container(
												padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
												decoration: BoxDecoration(
													color: AppColors.deepTeal.withOpacity(0.1),
													borderRadius: BorderRadius.circular(10),
												),
												child: Text(
													'${_notes.length}',
													style: TextStyle(
														color: AppColors.deepTeal,
														fontSize: 11,
														fontWeight: FontWeight.w600,
													),
												),
											),
										],
									),
									const SizedBox(height: 8),
									
									if (_notes.isEmpty)
										Card(
											child: Padding(
												padding: const EdgeInsets.all(16),
												child: Center(
													child: Column(
														mainAxisSize: MainAxisSize.min,
														children: [
															Icon(Icons.note_outlined, size: 32, color: AppColors.slateGrey),
															const SizedBox(height: 8),
															Text(
																'No notes yet',
																style: Theme.of(context).textTheme.bodySmall?.copyWith(
																	color: AppColors.slateGrey,
																),
															),
														],
													),
												),
											),
										)
									else
										..._notes.map((note) {
											final noteText = note['text'] as String?;
											final noteStatus = note['status'] as String? ?? 'pending';
											final createdAt = note['created_at'] as String?;
											
											return Card(
												margin: const EdgeInsets.only(bottom: 8),
												child: InkWell(
													onTap: () {
														// Could navigate to note detail in future
													},
													child: Padding(
														padding: const EdgeInsets.all(10),
														child: Column(
															crossAxisAlignment: CrossAxisAlignment.start,
															children: [
																Row(
																	children: [
																		Expanded(
																			child: Text(
																				DateFormat('MMM d • h:mm a').format(
																					createdAt != null
																						? DateTime.parse(createdAt).toLocal()
																						: DateTime.now(),
																				),
																				style: Theme.of(context).textTheme.bodySmall?.copyWith(
																					color: AppColors.slateGrey,
																					fontSize: 10,
																				),
																			),
																		),
																		Container(
																			padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
																			decoration: BoxDecoration(
																				color: (noteStatus == 'done' ? AppColors.emerald : AppColors.warmAmber).withOpacity(0.1),
																				borderRadius: BorderRadius.circular(8),
																			),
																			child: Text(
																				noteStatus,
																				style: TextStyle(
																					color: noteStatus == 'done' ? AppColors.emerald : AppColors.warmAmber,
																					fontSize: 9,
																					fontWeight: FontWeight.w600,
																				),
																			),
																		),
																	],
																),
																if (noteText != null && noteText.isNotEmpty) ...[
																	const SizedBox(height: 6),
																	Text(
																		noteText.length > 150 ? '${noteText.substring(0, 150)}...' : noteText,
																		style: Theme.of(context).textTheme.bodySmall?.copyWith(
																			fontSize: 12,
																		),
																		maxLines: 3,
																		overflow: TextOverflow.ellipsis,
																	),
																],
															],
														),
													),
												),
											);
										}).toList(),
								],
							),
						),
					),
		);
	}

	bool _hasEntities(Map<String, dynamic> entities) {
		return (entities['parts'] != null && (entities['parts'] as List).isNotEmpty) ||
			(entities['amounts'] != null && (entities['amounts'] as List).isNotEmpty) ||
			(entities['dates'] != null && (entities['dates'] as List).isNotEmpty);
	}
}

