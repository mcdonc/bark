import 'package:bark_plugin_api/bark_plugin_api.dart';
import 'beep.dart';

class BeepPlugin extends ToolPlugin {
  @override
  Map<String, ToolHandler> get handlers => {'beep': _handle};

  Future<String> _handle(Map<String, dynamic> request) async {
    final freq = (request['frequency'] as num?)?.toDouble() ?? 440;
    final dur = (request['duration'] as num?)?.toInt() ?? 600;
    playBeep(frequency: freq, durationMs: dur);
    return 'Beep played! (${freq}Hz, ${dur}ms)';
  }
}
