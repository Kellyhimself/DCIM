import 'dart:io';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../core/api_client.dart';
import '../core/session.dart';
import '../core/app_theme.dart';

class VoiceCaptureScreen extends StatefulWidget {
	final String? jobId;
	final String? clientId;
	
	const VoiceCaptureScreen({super.key, this.jobId, this.clientId});

	@override
	State<VoiceCaptureScreen> createState() => _VoiceCaptureScreenState();
}

class _VoiceCaptureScreenState extends State<VoiceCaptureScreen> {
	final _textCtrl = TextEditingController();
	final _recorder = AudioRecorder();
	bool _recording = false;
	String? _audioPath;
	bool _saving = false;
	String? _error;
	
	// Transcription tracking
	String? _currentNoteId;
	String _transcriptionStatus = 'pending'; // pending, transcribing, completed, failed
	Timer? _transcriptionPollTimer;
	bool _submitted = false; // Whether audio has been submitted and we're waiting for transcription
	String? _submittedNoteId; // Note ID that was submitted
	
	// Entity extraction (phones, amounts, dates, parts, client names, job types, locations)
	List<String> _discoveredPhones = [];
	List<String> _discoveredAmounts = [];
	List<String> _discoveredDates = [];
	List<String> _discoveredParts = [];
	List<String> _discoveredClientNames = [];
	List<String> _discoveredJobTypes = [];
	List<String> _discoveredLocations = [];
	bool _extractingEntities = false;
	
	// Entity linking suggestions
	List<Map<String, dynamic>> _linkSuggestions = [];
	List<Map<String, dynamic>> _selectedSuggestions = []; // User-selected suggestions to apply
	bool _loadingSuggestions = false;
	bool _applyingSuggestions = false; // Prevent double submissions

	ApiClient get _api => context.read<ApiClient>();
	Session get _session => context.read<Session>();

	Future<bool> _ensureMic() async {
		final status = await Permission.microphone.request();
		return status.isGranted;
	}

	Future<void> _toggleRecord() async {
		if (_recording) {
			final path = await _recorder.stop();
			setState(() { _recording = false; _audioPath = path; });
			return;
		}
		if (!await _ensureMic()) {
			setState(() => _error = 'Microphone permission denied');
			return;
		}
		// Stop any existing transcription polling
		_transcriptionPollTimer?.cancel();
		_transcriptionPollTimer = null;
		_currentNoteId = null;
		_submitted = false;
		_submittedNoteId = null;
		_discoveredPhones.clear();
		_discoveredAmounts.clear();
		_discoveredDates.clear();
		_discoveredParts.clear();
		_discoveredClientNames.clear();
		_discoveredJobTypes.clear();
		_discoveredLocations.clear();
		_linkSuggestions.clear();
		_selectedSuggestions.clear();
		
		final dir = await getTemporaryDirectory();
		final outPath = '${dir.path}/note-${DateTime.now().millisecondsSinceEpoch}.m4a';
		await _recorder.start(
			const RecordConfig(encoder: AudioEncoder.aacLc, sampleRate: 16000, bitRate: 64000),
			path: outPath,
		);
		setState(() { 
			_recording = true; 
			_audioPath = null; 
			_error = null;
			_transcriptionStatus = 'pending';
			_submitted = false;
			_submittedNoteId = null;
			_discoveredPhones.clear();
			_discoveredAmounts.clear();
			_discoveredDates.clear();
		});
	}

	Future<void> _extractEntities(String text) async {
		if (text.isEmpty) return;
		
		setState(() => _extractingEntities = true);
		_api.attachSession(_session);
		try {
			final resp = await _api.dio.post('/nlp/tag', data: {
				'text': text,
				'region': 'KE',
			});
			if (!mounted) return;
			
			final data = resp.data as Map<String, dynamic>;
			setState(() {
				_discoveredPhones = List<String>.from(data['phones'] ?? []);
				_discoveredAmounts = List<String>.from(data['amounts'] ?? []);
				_discoveredDates = List<String>.from(data['dates'] ?? []);
				_discoveredParts = List<String>.from(data['parts'] ?? []);
				_discoveredClientNames = List<String>.from(data['client_names'] ?? []);
				_discoveredJobTypes = List<String>.from(data['job_types'] ?? []);
				_discoveredLocations = List<String>.from(data['locations'] ?? []);
				_extractingEntities = false;
			});
			
			// Fetch link suggestions after entity extraction
			if (_submittedNoteId != null) {
				_fetchLinkSuggestions(_submittedNoteId!);
			}
		} catch (e) {
			print('Error extracting entities: $e');
			setState(() => _extractingEntities = false);
		}
	}
	
	Future<void> _fetchLinkSuggestions(String noteId) async {
		if (_submittedNoteId == null) return;
		
		setState(() => _loadingSuggestions = true);
		_api.attachSession(_session);
		try {
			final resp = await _api.dio.post('/notes/$noteId/link_suggestions');
			if (!mounted) return;
			
			final data = resp.data as Map<String, dynamic>;
			setState(() {
				_linkSuggestions = List<Map<String, dynamic>>.from(data['suggestions'] ?? []);
				_loadingSuggestions = false;
			});
		} catch (e) {
			print('Error fetching link suggestions: $e');
			setState(() => _loadingSuggestions = false);
		}
	}
	
	Future<void> _linkToClient(String clientId) async {
		if (_submittedNoteId == null) return;
		
		// Don't set _applyingSuggestions here - it's managed by the caller
		_api.attachSession(_session);
		try {
			await _api.dio.put('/notes/$_submittedNoteId', data: {
				'client_id': clientId,
			});
			
			// Refresh suggestions (but don't show snackbar if called from _applySelectedSuggestions)
			await _fetchLinkSuggestions(_submittedNoteId!);
			
			// Only show snackbar if not being called from _applySelectedSuggestions
			if (!_applyingSuggestions && mounted) {
				ScaffoldMessenger.of(context).showSnackBar(
					const SnackBar(
						content: Text('Note linked to client!'),
						duration: Duration(seconds: 2),
					),
				);
			}
		} catch (e) {
			print('Error linking to client: $e');
			// Don't show snackbar here if called from _applySelectedSuggestions
			if (!_applyingSuggestions && mounted) {
				ScaffoldMessenger.of(context).showSnackBar(
					SnackBar(
						content: Text('Failed to link: ${e.toString()}'),
						duration: const Duration(seconds: 2),
					),
				);
			}
			rethrow; // Re-throw so caller can handle
		}
	}
	
	Future<void> _createClientFromSuggestion(Map<String, dynamic> suggestion) async {
		// Don't set _applyingSuggestions here - it's managed by _applySelectedSuggestions
		// Note: This function can be called when _applyingSuggestions is true (from _applySelectedSuggestions)
		_api.attachSession(_session);
		try {
			final resp = await _api.dio.post('/clients', data: {
				'name': suggestion['name'] ?? '',
				'phone': suggestion['phone'],
				'location': suggestion['location'],
			});
			
			final clientId = resp.data['id'] as String;
			
			// Link note to newly created client
			if (_submittedNoteId != null) {
				await _linkToClient(clientId);
			}
		} catch (e) {
			print('Error creating client: $e');
			// Don't show snackbar here - let _applySelectedSuggestions handle it
			rethrow; // Re-throw so caller can count errors
		}
	}
	
	Future<void> _linkToJob(String jobId) async {
		if (_submittedNoteId == null) return;
		
		// Don't set _applyingSuggestions here - it's managed by the caller
		_api.attachSession(_session);
		try {
			await _api.dio.put('/notes/$_submittedNoteId', data: {
				'job_id': jobId,
			});
			
			// Refresh suggestions (but don't show snackbar if called from _applySelectedSuggestions)
			await _fetchLinkSuggestions(_submittedNoteId!);
			
			// Only show snackbar if not being called from _applySelectedSuggestions
			if (!_applyingSuggestions && mounted) {
				ScaffoldMessenger.of(context).showSnackBar(
					const SnackBar(
						content: Text('Note linked to job!'),
						duration: Duration(seconds: 2),
					),
				);
			}
		} catch (e) {
			print('Error linking to job: $e');
			// Don't show snackbar here if called from _applySelectedSuggestions
			if (!_applyingSuggestions && mounted) {
				ScaffoldMessenger.of(context).showSnackBar(
					SnackBar(
						content: Text('Failed to link: ${e.toString()}'),
						duration: const Duration(seconds: 2),
					),
				);
			}
			rethrow; // Re-throw so caller can handle
		}
	}
	
	Future<void> _createJobFromSuggestion(Map<String, dynamic> suggestion) async {
		// Don't set _applyingSuggestions here - it's managed by _applySelectedSuggestions
		// Note: This function can be called when _applyingSuggestions is true (from _applySelectedSuggestions)
		_api.attachSession(_session);
		try {
			var clientId = suggestion['client_id'] as String?;
			
			// If no client_id, try to find or create client from note's client_id
			if (clientId == null || clientId.isEmpty) {
				// Check if note has a client_id
				if (_submittedNoteId != null) {
					try {
						final noteResp = await _api.dio.get('/notes');
						final notes = noteResp.data as List;
						final currentNote = notes.firstWhere(
							(n) => (n as Map<String, dynamic>)['id'] == _submittedNoteId,
						) as Map<String, dynamic>?;
						
						if (currentNote != null) {
							final noteClientId = currentNote['client_id'] as String?;
							if (noteClientId != null) {
								clientId = noteClientId;
							}
						}
					} catch (e) {
						print('Error fetching note: $e');
					}
				}
				
				// If still no client_id, prompt user to create/link client first
				if (clientId == null || clientId.isEmpty) {
					throw Exception('Please create or link a client first');
				}
			}
			
			final resp = await _api.dio.post('/jobs', data: {
				'client_id': clientId,
				'site': suggestion['location'] ?? suggestion['name'] ?? '',
				'status': 'open',
			});
			
			final jobId = resp.data['id'] as String;
			
			// Link note to newly created job
			if (_submittedNoteId != null) {
				await _linkToJob(jobId);
			}
		} catch (e) {
			print('Error creating job: $e');
			// Don't show snackbar here - let _applySelectedSuggestions handle it
			rethrow; // Re-throw so caller can count errors
		}
	}
	
	Future<void> _applySelectedSuggestions() async {
		if (_selectedSuggestions.isEmpty || _applyingSuggestions) return;
		
		setState(() => _applyingSuggestions = true);
		
		int clientsCreated = 0;
		int clientsLinked = 0;
		int jobsCreated = 0;
		int jobsLinked = 0;
		int errors = 0;
		
		for (final suggestion in _selectedSuggestions) {
			final type = suggestion['type'] as String;
			final suggestionType = suggestion['suggestion'] as String;
			
			try {
				if (type == 'client') {
					if (suggestionType == 'link') {
						final clientId = suggestion['existing_client_id'] as String?;
						if (clientId != null) {
							await _linkToClient(clientId);
							clientsLinked++;
						}
					} else if (suggestionType == 'create') {
						await _createClientFromSuggestion(suggestion);
						clientsCreated++;
					}
				} else if (type == 'job') {
					if (suggestionType == 'link') {
						final jobId = suggestion['existing_job_id'] as String?;
						if (jobId != null) {
							await _linkToJob(jobId);
							jobsLinked++;
						}
					} else if (suggestionType == 'create') {
						await _createJobFromSuggestion(suggestion);
						jobsCreated++;
					}
				}
			} catch (e) {
				print('Error applying suggestion: $e');
				errors++;
			}
		}
		
		if (!mounted) return;
		setState(() {
			_applyingSuggestions = false;
			_selectedSuggestions.clear();
		});
		
		// Refresh suggestions after applying
		if (_submittedNoteId != null) {
			await _fetchLinkSuggestions(_submittedNoteId!);
		}
		
		// Show success message
		if (!mounted) return;
		final List<String> messages = [];
		if (clientsCreated > 0) messages.add('$clientsCreated client${clientsCreated > 1 ? 's' : ''} created');
		if (clientsLinked > 0) messages.add('$clientsLinked client${clientsLinked > 1 ? 's' : ''} linked');
		if (jobsCreated > 0) messages.add('$jobsCreated job${jobsCreated > 1 ? 's' : ''} created');
		if (jobsLinked > 0) messages.add('$jobsLinked job${jobsLinked > 1 ? 's' : ''} linked');
		
		if (messages.isNotEmpty) {
			ScaffoldMessenger.of(context).showSnackBar(
				SnackBar(
					content: Text(messages.join(', ')),
					duration: const Duration(seconds: 3),
					action: SnackBarAction(
						label: 'OK',
						onPressed: () {},
					),
				),
			);
		}
		
		if (errors > 0) {
			ScaffoldMessenger.of(context).showSnackBar(
				SnackBar(
					content: Text('$errors action${errors > 1 ? 's' : ''} failed'),
					backgroundColor: Colors.red,
					duration: const Duration(seconds: 2),
				),
			);
		}
	}
	
	Future<void> _shareNote() async {
		if (_submittedNoteId == null) {
			setState(() => _error = 'No note to share');
			return;
		}
		
		_api.attachSession(_session);
		try {
			final resp = await _api.dio.post('/notes/$_submittedNoteId/share_summary');
			final shareText = resp.data['text'] as String;
			
			await Share.share(shareText, subject: 'Voice Note Summary');
		} catch (e) {
			print('Error sharing note: $e');
			if (!mounted) return;
			ScaffoldMessenger.of(context).showSnackBar(
				SnackBar(
					content: Text('Failed to share: ${e.toString()}'),
					duration: const Duration(seconds: 2),
				),
			);
		}
	}

	Future<void> _checkTranscription(String noteId) async {
		_api.attachSession(_session);
		try {
			final resp = await _api.dio.get(
				'/notes',
				options: Options(
					sendTimeout: const Duration(seconds: 10),
					receiveTimeout: const Duration(seconds: 10),
				),
			);
			if (!mounted) return;
			
			final notes = resp.data as List;
			Map<String, dynamic>? currentNote;
			try {
				currentNote = notes.firstWhere(
					(n) => (n as Map<String, dynamic>)['id'] == noteId,
				) as Map<String, dynamic>?;
			} catch (_) {
				// Note not found, stop polling
				_transcriptionPollTimer?.cancel();
				_transcriptionPollTimer = null;
				_currentNoteId = null;
				return;
			}
			
			if (currentNote != null) {
				final status = currentNote['transcription_status'] as String? ?? 'pending';
				final text = currentNote['text'] as String?;
				
				final shouldExtractEntities = status == 'completed' && text != null && text.isNotEmpty && text != _textCtrl.text;
				final textToExtract = shouldExtractEntities ? text : null;
				
				setState(() {
					_transcriptionStatus = status;
					if (text != null && text.isNotEmpty && text != _textCtrl.text) {
						_textCtrl.text = text;
					}
				});
				
				// Extract entities when transcription completes (outside setState)
				if (textToExtract != null) {
					_extractEntities(textToExtract);
				}
				
				// Stop polling if transcription is completed or failed
				if (status == 'completed' || status == 'failed') {
					_transcriptionPollTimer?.cancel();
					_transcriptionPollTimer = null;
					_currentNoteId = null;
					// Keep _submitted true so user can review and save
				}
			}
		} on DioException catch (e) {
			// Connection errors - log but continue polling
			print('Error checking transcription: ${e.type} - ${e.message}');
			// Don't stop polling on connection errors - they might be temporary
		} catch (e) {
			print('Error checking transcription: $e');
			// Don't stop polling on unexpected errors either
		}
	}

	void _startTranscriptionPolling(String noteId) {
		_currentNoteId = noteId;
		_transcriptionStatus = 'pending';
		_transcriptionPollTimer?.cancel();
		
		// Poll every 2 seconds
		_transcriptionPollTimer = Timer.periodic(const Duration(seconds: 2), (timer) {
			if (_currentNoteId != null) {
				_checkTranscription(_currentNoteId!);
			} else {
				timer.cancel();
			}
		});
		
		// Also check immediately
		_checkTranscription(noteId);
	}

	Future<void> _submit() async {
		// Submit audio for transcription
		if (_audioPath == null) {
			setState(() => _error = 'No audio recorded');
			return;
		}
		
		setState(() { _saving = true; _error = null; });
		_api.attachSession(_session);
		try {
			// Create note first - include job_id and client_id if provided
			final noteData = <String, dynamic>{
				'text': null, // Will be filled by transcription
			};
			if (widget.jobId != null) {
				noteData['job_id'] = widget.jobId;
			}
			if (widget.clientId != null) {
				noteData['client_id'] = widget.clientId;
			}
			final createResp = await _api.dio.post('/notes', data: noteData);
			final note = createResp.data as Map<String, dynamic>;
			final noteId = note['id'] as String;
			_submittedNoteId = noteId;

			// Get presign to create media record
				final presign = await _api.dio.post(
					'/notes/$noteId/presign',
					queryParameters: {'kind': 'audio', 'content_type': 'audio/m4a'},
				);
				final p = presign.data as Map<String, dynamic>;
				final mediaId = p['media_id'] as String;
				final audioFile = File(_audioPath!);
			
			// Upload through backend API
			final fileBytes = await audioFile.readAsBytes();
			print('Uploading ${fileBytes.length} bytes through backend...');
			
			try {
				// Use FormData to upload file
				final formData = FormData.fromMap({
					'file': MultipartFile.fromBytes(
						fileBytes,
						filename: 'audio.m4a',
					),
				});
				
				await _api.dio.post(
					'/notes/$noteId/upload',
					queryParameters: {'media_id': mediaId},
					data: formData,
					options: Options(
						headers: {'Content-Type': 'multipart/form-data'},
					),
				);
				print('Upload successful');
			} on DioException catch (uploadError) {
				print('Upload error: ${uploadError.type} - ${uploadError.message}');
				if (uploadError.response != null) {
					print('Response status: ${uploadError.response!.statusCode}');
					print('Response data: ${uploadError.response!.data}');
				}
				setState(() => _error = 'Audio upload failed: ${uploadError.message ?? 'Upload failed'}');
				setState(() => _saving = false);
				return;
			} catch (e) {
				print('Unexpected upload error: $e');
				setState(() => _error = 'Audio upload failed: $e');
				setState(() => _saving = false);
				return;
			}

			if (!mounted) return;
			
			// Start polling for transcription
			_startTranscriptionPolling(noteId);
			
			setState(() { 
				_audioPath = null; 
				_recording = false;
				_saving = false;
				_submitted = true;
			});
			
			// No SnackBar - we'll show a banner instead
		} on DioException catch (e) {
			String errorMsg = 'Failed';
			if (e.response != null) {
				final data = e.response!.data;
				if (data is Map) {
					errorMsg = data['detail']?.toString() ?? data.toString();
				} else if (data is String) {
					errorMsg = data;
				} else {
					errorMsg = data?.toString() ?? 'Failed';
				}
			} else if (e.message != null) {
				errorMsg = e.message!;
			}
			setState(() => _error = errorMsg);
		} catch (e) {
			setState(() => _error = e.toString());
		} finally {
			setState(() => _saving = false);
		}
	}

	Future<void> _save() async {
		// Final save after transcription is complete
		if (_submittedNoteId == null) {
			setState(() => _error = 'No note to save');
			return;
		}
		
		setState(() { _saving = true; _error = null; });
		_api.attachSession(_session);
		try {
			// Update the note with the final text (user may have edited it)
			await _api.dio.put(
				'/notes/$_submittedNoteId',
				data: {
					'text': _textCtrl.text.trim().isEmpty ? null : _textCtrl.text.trim(),
				},
			);
			
			if (!mounted) return;
			
			setState(() { 
				_saving = false;
				_submitted = false;
				_submittedNoteId = null;
				_currentNoteId = null;
				_transcriptionStatus = 'pending';
				_textCtrl.clear();
				_discoveredPhones.clear();
				_discoveredAmounts.clear();
				_discoveredDates.clear();
			});
			
			ScaffoldMessenger.of(context).showSnackBar(
				const SnackBar(
					content: Text('Note saved successfully!'),
					duration: Duration(seconds: 2),
				),
			);
		} on DioException catch (e) {
			String errorMsg = 'Failed to save';
			if (e.response != null) {
				final data = e.response!.data;
				if (data is Map) {
					errorMsg = data['detail']?.toString() ?? data.toString();
				} else if (data is String) {
					errorMsg = data;
				} else {
					errorMsg = data?.toString() ?? 'Failed to save';
				}
			} else if (e.message != null) {
				errorMsg = e.message!;
			}
			setState(() => _error = errorMsg);
		} catch (e) {
			setState(() => _error = e.toString());
		} finally {
			setState(() => _saving = false);
		}
	}

	@override
	void initState() {
		super.initState();
	}

	@override
	void dispose() {
		_transcriptionPollTimer?.cancel();
		_textCtrl.dispose();
		_recorder.dispose();
		super.dispose();
	}

	@override
	Widget build(BuildContext context) {
		return Scaffold(
			appBar: AppBar(
				title: const Text('Record'),
			),
			body: SingleChildScrollView(
				child: Padding(
				padding: const EdgeInsets.all(16),
				child: Column(
					children: [
							// Recording controls
							SizedBox(
								height: 200,
							child: Center(
								child: SizedBox(
									height: 160,
									width: 160,
									child: FilledButton(
										onPressed: _saving ? null : _toggleRecord,
										style: FilledButton.styleFrom(
											shape: const CircleBorder(),
											padding: EdgeInsets.zero,
											backgroundColor: _recording ? AppColors.deepRed : AppColors.softCoral,
										),
										child: Icon(
											_recording ? Icons.stop : Icons.mic,
											size: 64,
											color: Colors.white,
										),
									),
								),
							),
						),
							// Transcription status badge
							if (_transcriptionStatus != 'pending' && _currentNoteId != null) ...[
								Container(
									padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
									decoration: BoxDecoration(
										color: _transcriptionStatus == 'transcribing'
											? AppColors.softCoral.withOpacity(0.1)
											: _transcriptionStatus == 'completed'
												? AppColors.emerald.withOpacity(0.1)
												: AppColors.deepRed.withOpacity(0.1),
										borderRadius: BorderRadius.circular(8),
										border: Border.all(
											color: _transcriptionStatus == 'transcribing'
												? AppColors.softCoral.withOpacity(0.3)
												: _transcriptionStatus == 'completed'
													? AppColors.emerald.withOpacity(0.3)
													: AppColors.deepRed.withOpacity(0.3),
										),
									),
									child: Row(
										mainAxisSize: MainAxisSize.min,
										children: [
											if (_transcriptionStatus == 'transcribing')
												SizedBox(
													width: 16,
													height: 16,
													child: CircularProgressIndicator(
														strokeWidth: 2,
														valueColor: AlwaysStoppedAnimation<Color>(AppColors.softCoral),
													),
												)
											else if (_transcriptionStatus == 'completed')
												Icon(Icons.check_circle, color: AppColors.emerald, size: 20)
											else
												Icon(Icons.error_outline, color: AppColors.deepRed, size: 20),
											const SizedBox(width: 8),
											Text(
												_transcriptionStatus == 'transcribing'
													? 'Transcribing...'
													: _transcriptionStatus == 'completed'
														? 'Transcription complete'
														: 'Transcription failed',
												style: TextStyle(
													color: _transcriptionStatus == 'transcribing'
														? AppColors.softCoral
														: _transcriptionStatus == 'completed'
															? AppColors.emerald
															: AppColors.deepRed,
													fontWeight: FontWeight.w600,
													fontSize: 13,
												),
											),
										],
									),
								),
								const SizedBox(height: 12),
							],
						TextField(
							controller: _textCtrl,
								maxLines: _transcriptionStatus == 'completed' ? null : 3,
								minLines: _transcriptionStatus == 'completed' ? 5 : 1,
								decoration: InputDecoration(
									labelText: _transcriptionStatus == 'transcribing' 
										? 'Transcribing your voice...'
										: _transcriptionStatus == 'completed'
											? 'Transcribed text (you can edit)'
											: 'Note text',
									hintText: _transcriptionStatus == 'transcribing'
										? 'Please wait while we transcribe your recording...'
										: 'Type or wait for transcription...',
									suffixIcon: _transcriptionStatus == 'transcribing'
										? const Padding(
											padding: EdgeInsets.all(12),
											child: SizedBox(
												width: 20,
												height: 20,
												child: CircularProgressIndicator(strokeWidth: 2),
											),
										)
										: null,
								),
								enabled: true, // Always enabled so user can type manually
						),
						const SizedBox(height: 12),
						if (_audioPath != null)
							Align(
								alignment: Alignment.centerLeft,
								child: Container(
									padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
									decoration: BoxDecoration(
										color: AppColors.emerald.withOpacity(0.1),
										borderRadius: BorderRadius.circular(8),
									),
									child: Row(
										mainAxisSize: MainAxisSize.min,
										children: [
											Icon(Icons.check_circle, color: AppColors.emerald, size: 20),
											const SizedBox(width: 8),
											Text(
													'Audio recorded - ready to submit',
												style: TextStyle(color: AppColors.emerald, fontWeight: FontWeight.w600),
											),
										],
									),
								),
							),
							// Subtle status indicator when transcription is in progress
							if (_submitted && _transcriptionStatus == 'transcribing') ...[
								const SizedBox(height: 8),
								Row(
									children: [
										SizedBox(
											width: 12,
											height: 12,
											child: CircularProgressIndicator(
												strokeWidth: 2,
												valueColor: AlwaysStoppedAnimation<Color>(AppColors.softCoral),
											),
										),
										const SizedBox(width: 8),
										Text(
											'Transcribing in background...',
											style: TextStyle(
												color: AppColors.softCoral,
												fontSize: 12,
												fontStyle: FontStyle.italic,
											),
										),
									],
								),
							],
							// Entity extraction indicator
							if (_transcriptionStatus == 'completed' && _extractingEntities) ...[
								const SizedBox(height: 8),
								Row(
									children: [
										SizedBox(
											width: 12,
											height: 12,
											child: CircularProgressIndicator(
												strokeWidth: 2,
												valueColor: AlwaysStoppedAnimation<Color>(AppColors.softCoral),
											),
										),
										const SizedBox(width: 8),
										Text(
											'Extracting entities...',
											style: TextStyle(
												color: AppColors.softCoral,
												fontSize: 12,
												fontStyle: FontStyle.italic,
											),
										),
									],
								),
							],
							// Compact entity summary (optional, minimal display)
							if (_transcriptionStatus == 'completed' && !_extractingEntities && (
								_discoveredPhones.isNotEmpty || 
								_discoveredAmounts.isNotEmpty || 
								_discoveredDates.isNotEmpty ||
								_discoveredParts.isNotEmpty ||
								_discoveredClientNames.isNotEmpty ||
								_discoveredJobTypes.isNotEmpty ||
								_discoveredLocations.isNotEmpty
							)) ...[
								const SizedBox(height: 8),
								Container(
									padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
									decoration: BoxDecoration(
										color: AppColors.softCoral.withOpacity(0.05),
										borderRadius: BorderRadius.circular(6),
									),
									child: Row(
										mainAxisSize: MainAxisSize.min,
										children: [
											Icon(Icons.info_outline, size: 14, color: AppColors.softCoral),
											const SizedBox(width: 6),
											Text(
												'${_discoveredPhones.length + _discoveredAmounts.length + _discoveredDates.length + _discoveredParts.length + _discoveredClientNames.length + _discoveredJobTypes.length + _discoveredLocations.length} entities found',
												style: TextStyle(
													fontSize: 11,
													color: AppColors.softCoral,
													fontStyle: FontStyle.italic,
												),
											),
										],
									),
								),
							],
							// Quick Actions - Compact selection-based UI
							if (_transcriptionStatus == 'completed' && _linkSuggestions.isNotEmpty) ...[
								const SizedBox(height: 12),
								Container(
									padding: const EdgeInsets.all(10),
									decoration: BoxDecoration(
										color: AppColors.softCoral.withOpacity(0.05),
										borderRadius: BorderRadius.circular(8),
										border: Border.all(color: AppColors.softCoral.withOpacity(0.2)),
									),
									child: Column(
										crossAxisAlignment: CrossAxisAlignment.start,
										mainAxisSize: MainAxisSize.min,
										children: [
											Row(
												children: [
													Icon(Icons.lightbulb_outline, size: 16, color: AppColors.softCoral),
													const SizedBox(width: 6),
													Text(
														'Quick Actions',
														style: TextStyle(
															fontWeight: FontWeight.w600,
															color: AppColors.softCoral,
															fontSize: 13,
														),
													),
													const Spacer(),
													if (_loadingSuggestions)
														SizedBox(
															width: 14,
															height: 14,
															child: CircularProgressIndicator(
																strokeWidth: 2,
																valueColor: AlwaysStoppedAnimation<Color>(AppColors.softCoral),
															),
														),
												],
											),
											if (!_loadingSuggestions) ...[
												const SizedBox(height: 8),
												..._linkSuggestions.map((suggestion) {
													final suggestionId = '${suggestion['type']}_${suggestion['suggestion']}_${suggestion['name']}_${suggestion['existing_client_id'] ?? suggestion['existing_job_id'] ?? ''}';
													final isSelected = _selectedSuggestions.any((s) => 
														'${s['type']}_${s['suggestion']}_${s['name']}_${s['existing_client_id'] ?? s['existing_job_id'] ?? ''}' == suggestionId
													);
													final type = suggestion['type'] as String;
													final suggestionType = suggestion['suggestion'] as String;
													final name = suggestion['name'] as String? ?? '';
													final phone = suggestion['phone'] as String?;
													
													String label = '';
													IconData icon = Icons.info;
													Color color = AppColors.softCoral;
													
													if (type == 'client') {
														if (suggestionType == 'link') {
															label = 'Link to ${name.isNotEmpty ? name : "client"}';
															icon = Icons.link;
															color = AppColors.softCoral;
														} else {
															label = 'Create: ${name.isNotEmpty ? name : phone ?? "New client"}';
															icon = Icons.person_add;
															color = AppColors.emerald;
														}
													} else if (type == 'job') {
														if (suggestionType == 'link') {
															label = 'Link to job: ${suggestion['name'] ?? "job"}';
															icon = Icons.link;
															color = AppColors.softCoral;
														} else {
															// Use name if available (already formatted as "job_type - location")
															// Otherwise construct from job_type and location
															final jobType = suggestion['job_type'] as String?;
															final location = suggestion['location'] as String?;
															if (suggestion['name'] != null && (suggestion['name'] as String).isNotEmpty) {
																label = suggestion['name'] as String;
															} else if (jobType != null && location != null) {
																label = '$jobType - $location';
															} else if (jobType != null) {
																label = jobType;
															} else if (location != null) {
																label = location;
															} else {
																label = 'New job';
															}
															icon = Icons.work_outline;
															color = AppColors.softCoral;
														}
													}
													
													return Padding(
														padding: const EdgeInsets.only(bottom: 6),
														child: InkWell(
															onTap: () {
																setState(() {
																	if (isSelected) {
																		_selectedSuggestions.removeWhere((s) => 
																			'${s['type']}_${s['suggestion']}_${s['name']}_${s['existing_client_id'] ?? s['existing_job_id'] ?? ''}' == suggestionId
																		);
																	} else {
																		_selectedSuggestions.add(suggestion);
																	}
																});
															},
															borderRadius: BorderRadius.circular(6),
															child: Container(
																padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
																decoration: BoxDecoration(
																	color: isSelected ? color.withOpacity(0.15) : Colors.transparent,
																	borderRadius: BorderRadius.circular(6),
																	border: Border.all(
																		color: isSelected ? color : Colors.transparent,
																		width: 1,
																	),
																),
																child: Row(
																	children: [
																		Checkbox(
																			value: isSelected,
																			onChanged: (val) {
																				setState(() {
																					if (val == true) {
																						_selectedSuggestions.add(suggestion);
																					} else {
																						_selectedSuggestions.removeWhere((s) => 
																							'${s['type']}_${s['suggestion']}_${s['name']}_${s['existing_client_id'] ?? s['existing_job_id'] ?? ''}' == suggestionId
																						);
																					}
																				});
																			},
																			visualDensity: VisualDensity.compact,
																			materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
																		),
																		Icon(icon, size: 14, color: color),
																		const SizedBox(width: 6),
																		Expanded(
																			child: Text(
																				label,
																				style: TextStyle(
																					fontSize: 12,
																					color: color,
																					fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
																				),
																			),
																		),
																		IconButton(
																			icon: Icon(Icons.close, size: 16, color: Colors.grey),
																			onPressed: () {
																				setState(() {
																					_linkSuggestions.removeWhere((s) => 
																						'${s['type']}_${s['suggestion']}_${s['name']}_${s['existing_client_id'] ?? s['existing_job_id'] ?? ''}' == suggestionId
																					);
																					_selectedSuggestions.removeWhere((s) => 
																						'${s['type']}_${s['suggestion']}_${s['name']}_${s['existing_client_id'] ?? s['existing_job_id'] ?? ''}' == suggestionId
																					);
																				});
																			},
																			padding: EdgeInsets.zero,
																			constraints: const BoxConstraints(),
																			visualDensity: VisualDensity.compact,
																			tooltip: 'Remove',
																		),
																	],
																),
															),
														),
													);
												}),
												if (_selectedSuggestions.isNotEmpty) ...[
													const SizedBox(height: 8),
													SizedBox(
														width: double.infinity,
														child: FilledButton.icon(
															onPressed: _applyingSuggestions ? null : _applySelectedSuggestions,
															icon: _applyingSuggestions
																? const SizedBox(
																	width: 14,
																	height: 14,
																	child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
																)
																: const Icon(Icons.check, size: 16),
															label: Text(_applyingSuggestions ? 'Applying...' : 'Apply ${_selectedSuggestions.length} action${_selectedSuggestions.length > 1 ? 's' : ''}'),
															style: FilledButton.styleFrom(
																backgroundColor: AppColors.softCoral,
																padding: const EdgeInsets.symmetric(vertical: 10),
															),
														),
													),
												],
											],
										],
									),
								),
							],
						if (_error != null) ...[
							const SizedBox(height: 8),
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
						const SizedBox(height: 8),
							// Share button (only show when transcription is completed)
							if (_submitted && _transcriptionStatus == 'completed') ...[
								SizedBox(
									width: double.infinity,
									child: OutlinedButton.icon(
										onPressed: _saving ? null : _shareNote,
										icon: const Icon(Icons.share),
										label: const Text('Share via WhatsApp'),
										style: OutlinedButton.styleFrom(
											foregroundColor: AppColors.softCoral,
											side: BorderSide(color: AppColors.softCoral),
										),
									),
								),
								const SizedBox(height: 8),
							],
						SizedBox(
							width: double.infinity,
							child: FilledButton(
									onPressed: (_saving || _recording) ? null : (_submitted && (_transcriptionStatus == 'completed' || _transcriptionStatus == 'failed') ? _save : _audioPath != null ? _submit : null),
									style: FilledButton.styleFrom(
										backgroundColor: _submitted && _transcriptionStatus == 'completed' 
											? AppColors.emerald 
											: AppColors.softCoral,
									),
								child: _saving
									? const SizedBox(
										height: 20,
										width: 20,
										child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
									)
										: Text(
											_submitted && _transcriptionStatus == 'completed'
												? 'Save Note'
												: _submitted && _transcriptionStatus == 'transcribing'
													? 'Transcribing... (please wait)'
													: _submitted && _transcriptionStatus == 'failed'
														? 'Save Note (transcription failed)'
														: _audioPath != null
															? 'Submit for Transcription'
															: 'No audio recorded',
										),
							),
						),
					],
					),
				),
			),
		);
	}
}
