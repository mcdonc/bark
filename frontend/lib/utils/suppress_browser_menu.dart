import 'dart:html' as html;
import 'package:flutter/widgets.dart';

/// Suppresses the browser's native context menu within this widget's area.
/// Use this to wrap areas where Flutter handles right-click via onSecondaryTapDown.
class SuppressBrowserContextMenu extends StatefulWidget {
  final Widget child;

  const SuppressBrowserContextMenu({super.key, required this.child});

  @override
  State<SuppressBrowserContextMenu> createState() =>
      _SuppressBrowserContextMenuState();
}

class _SuppressBrowserContextMenuState
    extends State<SuppressBrowserContextMenu> {
  void _onContextMenu(html.Event event) {
    event.preventDefault();
  }

  @override
  void initState() {
    super.initState();
    // We suppress globally but only when this widget is mounted.
    // Multiple instances will stack — that's fine since preventDefault is idempotent.
  }

  @override
  Widget build(BuildContext context) {
    return Listener(
      onPointerDown: (event) {
        // Right mouse button = 2
        if (event.buttons == 2) {
          // Suppress the browser context menu for this click
          html.document.addEventListener('contextmenu', _onContextMenu);
          Future.delayed(const Duration(milliseconds: 100), () {
            html.document.removeEventListener('contextmenu', _onContextMenu);
          });
        }
      },
      child: widget.child,
    );
  }
}
