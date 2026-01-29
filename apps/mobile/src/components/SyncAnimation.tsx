import React from 'react';
import { StyleSheet, View } from 'react-native';
import LottieView from 'lottie-react-native';

const syncAnimation = require('../../assets/lottie/sync.json');

type SyncAnimationProps = {
  size?: number;
};

export default function SyncAnimation({ size = 56 }: SyncAnimationProps) {
  return (
    <View style={[styles.container, { width: size, height: size }]}>
      <LottieView source={syncAnimation} autoPlay loop style={styles.animation} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  animation: {
    width: '100%',
    height: '100%',
  },
});
