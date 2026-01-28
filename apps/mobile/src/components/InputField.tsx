import React from 'react';
import { StyleSheet, Text, TextInput, TextInputProps, View } from 'react-native';

import { colors, radius, spacing } from '../theme';

type InputFieldProps = TextInputProps & {
  label?: string;
  helperText?: string;
  errorText?: string;
};

export default function InputField({ label, helperText, errorText, style, ...rest }: InputFieldProps) {
  const hasError = Boolean(errorText);
  return (
    <View style={styles.container}>
      {label ? <Text style={styles.label}>{label}</Text> : null}
      <TextInput
        style={[styles.input, hasError && styles.inputError, style]}
        placeholderTextColor={colors.textSecondary}
        {...rest}
      />
      {helperText && !hasError ? <Text style={styles.helper}>{helperText}</Text> : null}
      {hasError ? <Text style={styles.error}>{errorText}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: spacing.md,
  },
  label: {
    marginBottom: spacing.xs,
    color: colors.textSecondary,
    fontWeight: '600',
    fontSize: 12,
  },
  input: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    color: colors.textPrimary,
  },
  inputError: {
    borderColor: colors.danger,
  },
  helper: {
    marginTop: spacing.xs,
    color: colors.textSecondary,
    fontSize: 12,
  },
  error: {
    marginTop: spacing.xs,
    color: colors.danger,
    fontSize: 12,
  },
});
