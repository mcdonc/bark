import 'dart:async';
import 'package:flutter/widgets.dart';

/// Handler that receives a request map and returns a response string.
typedef ToolHandler = Future<String> Function(Map<String, dynamic> request);

/// A plugin that provides tool action handlers and optional overlay UI.
abstract class ToolPlugin {
  /// Action names this plugin handles.
  Map<String, ToolHandler> get handlers;

  /// Optional overlay widget to mount in the workspace Stack.
  /// Return null if this plugin has no UI.
  Widget? buildOverlay(BuildContext context) => null;

  /// Called when the plugin is disposed.
  void dispose() {}
}

/// Registry of tool plugins.
class ToolPluginRegistry {
  static final ToolPluginRegistry _instance = ToolPluginRegistry._();
  factory ToolPluginRegistry() => _instance;
  ToolPluginRegistry._();

  final List<ToolPlugin> _plugins = [];
  final Map<String, ToolHandler> _handlers = {};

  /// Register a plugin. Call during app startup.
  void register(ToolPlugin plugin) {
    _plugins.add(plugin);
    _handlers.addAll(plugin.handlers);
  }

  /// All registered plugins.
  List<ToolPlugin> get plugins => List.unmodifiable(_plugins);

  /// Dispatch an action to the appropriate handler.
  Future<String> dispatch(String action, Map<String, dynamic> request) async {
    final handler = _handlers[action];
    if (handler == null) {
      return 'Unknown action: $action';
    }
    return handler(request);
  }

  /// Dispose all plugins.
  void disposeAll() {
    for (final plugin in _plugins) {
      plugin.dispose();
    }
  }
}
