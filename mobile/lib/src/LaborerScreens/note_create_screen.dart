import 'dart:io';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';

import '../core/api_client.dart';
import '../core/session.dart';
import '../core/app_theme.dart';

class NoteCreateScreen extends StatefulWidget {
	const NoteCreateScreen({super.key});

	@override
	State<NoteCreateScreen> createState() => _NoteCreateScreenState();
}

class _NoteCreateScreenState extends State<NoteCreateScreen> {
	final _formKey = GlobalKey<FormState>();
	final _textCtrl = TextEditingController();
	bool _saving = false;
	String? _error;

	final _recorder = AudioRecorder();
	bool _recording = false;
	String? _audioPath;

	Future<bool> _ensureMic() async {
		final status = await Permission.microphone.request();
		return status.isGranted;
	}

	Future<void> _toggleRecord() async {
		if (_recording) {
			final path = await _recorder.stop();
			setState(() {
				_recording = false;
				_audioPath = path;
			});
			return;
		}
		if (!await _ensureMic()) {
			setState(() => _error = 'Microphone permission denied');
			return;
		}
		final dir = await getTemporaryDirectory();
		final outPath = '${dir.path}/note-${DateTime.now().millisecondsSinceEpoch}.m4a';
		await _recorder.start(
			const RecordConfig(encoder: AudioEncoder.aacLc, sampleRate: 16000, bitRate: 64000),
			path: outPath,
		);
		setState(() {
			_recording = true;
			_audioPath = null;
		});
	}

	Future<void> _save() async {
		if (!_formKey.currentState!.validate()) return;
		setState(() {
			_saving = true;
			_error = null;
		});
		final api = context.read<ApiClient>();
		final session = context.read<Session>();
		api.attachSession(session);
		try {
			// 1) Create note (text only)
			final createResp = await api.dio.post('/notes', data: {
				'text': _textCtrl.text.trim(),
			});
			final note = createResp.data as Map<String, dynamic>;
			final noteId = note['id'] as String;

			// 2) If audio recorded, presign + PUT + finalize
			if (_audioPath != null) {
				final presign = await api.dio.post(
					'/notes/$noteId/presign',
					queryParameters: {'kind': 'audio', 'content_type': 'audio/m4a'},
				);
				final p = presign.data as Map<String, dynamic>;
				final url = p['upload_url'] as String;
				final mediaId = p['media_id'] as String;
				final audioFile = File(_audioPath!);
				await Dio().put(
					url,
					data: audioFile.openRead(),
					options: Options(headers: {'Content-Type': 'audio/m4a'}),
				);
				await api.dio.post(
					'/notes/$noteId/finalize',
					queryParameters: {'media_id': mediaId},
				);
			}

			if (mounted) Navigator.of(context).pop();
		} on DioException catch (e) {
			setState(() => _error = e.response?.data?.toString() ?? 'Failed');
		} finally {
			setState(() => _saving = false);
		}
	}

	@override
	void dispose() {
		_textCtrl.dispose();
		_recorder.dispose();
		super.dispose();
	}

	@override
	Widget build(BuildContext context) {
		final canSave = !_saving && (!_recording);
		return Scaffold(
			appBar: AppBar(title: const Text('New note')),
			body: Padding(
				padding: const EdgeInsets.all(16),
				child: Form(
					key: _formKey,
					child: Column(
						children: [
							TextFormField(
								controller: _textCtrl,
								maxLines: 6,
								decoration: const InputDecoration(labelText: 'What happened?'),
								validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
							),
							const SizedBox(height: 16),
							Row(
								children: [
									FilledButton.icon(
										onPressed: _saving ? null : _toggleRecord,
										icon: Icon(_recording ? Icons.stop : Icons.mic),
										label: Text(_recording ? 'Stop' : 'Record'),
									),
									const SizedBox(width: 12),
									if (_audioPath != null)
										Container(
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
														'Audio attached',
														style: TextStyle(color: AppColors.emerald, fontWeight: FontWeight.w600),
													),
												],
											),
										),
								],
							),
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
							const Spacer(),
							SizedBox(
								width: double.infinity,
								child: FilledButton(
									onPressed: canSave ? _save : null,
									child: _saving
										? const SizedBox(
											height: 20,
											width: 20,
											child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
										)
										: const Text('Save'),
								),
							),
						],
					),
				),
			),
		);
	}
}
