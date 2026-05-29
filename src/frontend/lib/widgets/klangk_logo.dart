import 'package:flutter/material.dart';

/// Klangk logo widget — orange rounded square with robot icon on top and "Klangk" text below.
class KlangkLogo extends StatelessWidget {
  final double height;

  const KlangkLogo({super.key, this.height = 40});

  @override
  Widget build(BuildContext context) {
    final iconSize = height * 0.5;
    final fontSize = height * 0.2;
    final radius = height * 0.18;

    return Container(
      width: height,
      height: height,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(radius),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFFFF8C00), Color(0xFFE06800)],
        ),
        boxShadow: const [
          BoxShadow(
              color: Color(0x30000000), blurRadius: 3, offset: Offset(1, 1)),
        ],
      ),
      child: FittedBox(
        fit: BoxFit.scaleDown,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.smart_toy_outlined, color: Colors.white, size: iconSize),
            Text(
              'klangk',
              style: TextStyle(
                fontSize: fontSize,
                fontWeight: FontWeight.w400,
                color: Colors.white,
                letterSpacing: 0.5,
                height: 1.1,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
