import React from 'react';
import { StyleSheet, View } from 'react-native';

import { colors } from '../theme';

type MiniBarChartProps = {
  data: number[];
  height?: number;
  positiveColor?: string;
  negativeColor?: string;
};

export default function MiniBarChart({
  data,
  height = 64,
  positiveColor = colors.primary,
  negativeColor = colors.warning,
}: MiniBarChartProps) {
  if (!data.length) {
    return null;
  }
  const max = Math.max(...data.map((value) => Math.abs(value)), 1);

  return (
    <View style={[styles.container, { height }]}>
      {data.map((value, index) => {
        const barHeight = (Math.abs(value) / max) * height;
        return (
          <View
            key={`${index}-${value}`}
            style={[styles.barWrap, index === data.length - 1 && styles.barWrapLast]}
          >
            <View
              style={[
                styles.bar,
                {
                  height: barHeight,
                  backgroundColor: value >= 0 ? positiveColor : negativeColor,
                },
              ]}
            />
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'flex-end',
  },
  barWrap: {
    flex: 1,
    marginRight: 6,
    alignItems: 'center',
    justifyContent: 'flex-end',
  },
  barWrapLast: {
    marginRight: 0,
  },
  bar: {
    width: '100%',
    borderRadius: 6,
  },
});
