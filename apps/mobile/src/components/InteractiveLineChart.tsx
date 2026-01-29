import React, { useEffect, useMemo, useState } from 'react';
import { LayoutChangeEvent, StyleSheet, Text, View } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useDerivedValue,
  useSharedValue,
} from 'react-native-reanimated';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Svg, { Circle, Defs, LinearGradient, Line, Path, Stop } from 'react-native-svg';

import { colors, spacing } from '../theme';

type InteractiveLineChartProps = {
  data: number[];
  height?: number;
  strokeColor?: string;
  gradientFrom?: string;
  gradientTo?: string;
  label?: string;
  valueFormatter?: (value: number) => string;
  enableZoom?: boolean;
};

export default function InteractiveLineChart({
  data,
  height = 120,
  strokeColor = colors.primary,
  gradientFrom = 'rgba(37, 99, 235, 0.2)',
  gradientTo = 'rgba(37, 99, 235, 0.0)',
  label,
  valueFormatter,
  enableZoom = false,
}: InteractiveLineChartProps) {
  const [width, setWidth] = useState(0);
  const [selectedIndex, setSelectedIndex] = useState(Math.max(data.length - 1, 0));
  const scale = useSharedValue(1);
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);
  const containerWidth = useSharedValue(0);
  const containerHeight = useSharedValue(0);
  const startScale = useSharedValue(1);
  const startX = useSharedValue(0);
  const startY = useSharedValue(0);

  useEffect(() => {
    if (data.length) {
      setSelectedIndex(Math.max(data.length - 1, 0));
    }
  }, [data.length]);

  const onLayout = (event: LayoutChangeEvent) => {
    const nextWidth = event.nativeEvent.layout.width;
    if (nextWidth !== width) {
      setWidth(nextWidth);
    }
    containerWidth.value = nextWidth;
    containerHeight.value = event.nativeEvent.layout.height;
  };

  const { path, areaPath, points, min, max } = useMemo(() => {
    if (!data.length || width === 0) {
      return { path: '', areaPath: '', points: [], min: 0, max: 0 };
    }
    const minValue = Math.min(...data);
    const maxValue = Math.max(...data);
    const range = maxValue - minValue || 1;
    const chartPoints = data.map((value, index) => {
      const x = (index / Math.max(data.length - 1, 1)) * width;
      const y = height - ((value - minValue) / range) * height;
      return { x, y, value };
    });
    const linePath = chartPoints
      .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`)
      .join(' ');
    const area = `${linePath} L ${width} ${height} L 0 ${height} Z`;
    return { path: linePath, areaPath: area, points: chartPoints, min: minValue, max: maxValue };
  }, [data, height, width]);

  const selectedPoint = points[selectedIndex];
  const displayValue = selectedPoint?.value ?? data[0];
  const displayLabel = typeof displayValue === 'number'
    ? (valueFormatter ? valueFormatter(displayValue) : displayValue.toFixed(2))
    : '--';

  const handleTouch = (event: any) => {
    if (!width || data.length <= 1) return;
    const x = event.nativeEvent.locationX;
    const index = Math.round((x / width) * (data.length - 1));
    setSelectedIndex(Math.max(0, Math.min(data.length - 1, index)));
  };

  const maxTranslateX = useDerivedValue(() => (containerWidth.value * (scale.value - 1)) / 2);
  const maxTranslateY = useDerivedValue(() => (containerHeight.value * (scale.value - 1)) / 2);

  const clamp = (value: number, min: number, max: number) => {
    'worklet';
    return Math.min(Math.max(value, min), max);
  };

  const pinchGesture = Gesture.Pinch()
    .onBegin(() => {
      startScale.value = scale.value;
    })
    .onUpdate((event) => {
      const nextScale = clamp(startScale.value * event.scale, 1, 2.5);
      scale.value = nextScale;
      translateX.value = clamp(translateX.value, -maxTranslateX.value, maxTranslateX.value);
      translateY.value = clamp(translateY.value, -maxTranslateY.value, maxTranslateY.value);
    })
    .onEnd(() => {
      if (scale.value < 1) {
        scale.value = 1;
        translateX.value = 0;
        translateY.value = 0;
      }
    });

  const panGesture = Gesture.Pan()
    .onBegin(() => {
      startX.value = translateX.value;
      startY.value = translateY.value;
    })
    .onUpdate((event) => {
      translateX.value = clamp(startX.value + event.translationX, -maxTranslateX.value, maxTranslateX.value);
      translateY.value = clamp(startY.value + event.translationY, -maxTranslateY.value, maxTranslateY.value);
    });

  const chartStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: translateX.value },
      { translateY: translateY.value },
      { scale: scale.value },
    ],
  }));

  return (
    <View
      onLayout={onLayout}
      style={[styles.container, { height }]}
      onStartShouldSetResponder={() => true}
      onMoveShouldSetResponder={() => true}
      onResponderGrant={enableZoom ? undefined : handleTouch}
      onResponderMove={enableZoom ? undefined : handleTouch}
    >
      {path ? (
        enableZoom ? (
          <GestureDetector gesture={Gesture.Simultaneous(pinchGesture, panGesture)}>
            <Animated.View style={chartStyle}>
              <Svg width={width} height={height}>
                <Defs>
                  <LinearGradient id="lineGradient" x1="0" y1="0" x2="0" y2="1">
                    <Stop offset="0" stopColor={gradientFrom} stopOpacity="1" />
                    <Stop offset="1" stopColor={gradientTo} stopOpacity="1" />
                  </LinearGradient>
                </Defs>
                <Path d={areaPath} fill="url(#lineGradient)" />
                <Path d={path} stroke={strokeColor} strokeWidth={3} fill="none" />
                {selectedPoint ? (
                  <Line
                    x1={selectedPoint.x}
                    y1={0}
                    x2={selectedPoint.x}
                    y2={height}
                    stroke="rgba(148, 163, 184, 0.6)"
                    strokeDasharray="4 4"
                  />
                ) : null}
                {selectedPoint ? (
                  <Circle cx={selectedPoint.x} cy={selectedPoint.y} r={5} fill={colors.surface} stroke={strokeColor} strokeWidth={2} />
                ) : null}
              </Svg>
            </Animated.View>
          </GestureDetector>
        ) : (
          <View>
            <Svg width={width} height={height}>
              <Defs>
                <LinearGradient id="lineGradient" x1="0" y1="0" x2="0" y2="1">
                  <Stop offset="0" stopColor={gradientFrom} stopOpacity="1" />
                  <Stop offset="1" stopColor={gradientTo} stopOpacity="1" />
                </LinearGradient>
              </Defs>
              <Path d={areaPath} fill="url(#lineGradient)" />
              <Path d={path} stroke={strokeColor} strokeWidth={3} fill="none" />
              {selectedPoint ? (
                <Line
                  x1={selectedPoint.x}
                  y1={0}
                  x2={selectedPoint.x}
                  y2={height}
                  stroke="rgba(148, 163, 184, 0.6)"
                  strokeDasharray="4 4"
                />
              ) : null}
              {selectedPoint ? (
                <Circle cx={selectedPoint.x} cy={selectedPoint.y} r={5} fill={colors.surface} stroke={strokeColor} strokeWidth={2} />
              ) : null}
            </Svg>
          </View>
        )
      ) : (
        <View style={styles.placeholder} />
      )}
      <View style={styles.labelRow}>
        {label ? <Text style={styles.label}>{label}</Text> : null}
        <Text style={styles.value}>{displayLabel ?? '--'}</Text>
      </View>
      {path ? (
        <Text style={styles.range}>{`${min.toFixed(2)} → ${max.toFixed(2)}`}</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: '100%',
  },
  placeholder: {
    height: '100%',
    backgroundColor: colors.surfaceAlt,
    borderRadius: 16,
  },
  labelRow: {
    marginTop: spacing.sm,
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  label: {
    color: colors.textSecondary,
    fontSize: 12,
  },
  value: {
    color: colors.textPrimary,
    fontWeight: '700',
    fontSize: 12,
  },
  range: {
    marginTop: spacing.xs,
    color: colors.textSecondary,
    fontSize: 11,
  },
});
